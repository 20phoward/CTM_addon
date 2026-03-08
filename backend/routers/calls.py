from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

import logging

from database import get_db, Call, CallScore, User
from models.schemas import (
    CallSummary, CallDetail, CallStatusResponse, DashboardStats,
    CallScoreResponse, CallAssignRequest,
)
from config import STORAGE_DIR
from dependencies import get_current_user, get_call_scope_filter, require_supervisor_or_admin
from services.audit import log_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _check_call_access(call, scope_filter, db):
    """Verify user can access this specific call."""
    q = db.query(Call).filter(Call.id == call.id)
    q = scope_filter(q, Call, db)
    if q.first() is None:
        raise HTTPException(status_code=403, detail="Access denied")


@router.get("", response_model=list[CallSummary])
def list_calls(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope_filter=Depends(get_call_scope_filter),
):
    query = db.query(Call).order_by(Call.call_date.desc().nullslast())
    query = scope_filter(query, Call, db)
    calls = query.all()

    results = []
    for c in calls:
        rep_name = None
        if c.rep_id:
            rep = db.query(User).filter(User.id == c.rep_id).first()
            rep_name = rep.name if rep else None
        results.append(CallSummary(
            id=c.id,
            call_date=c.call_date,
            duration=c.duration,
            status=c.status,
            source_type=c.source_type,
            campaign_name=c.campaign_name,
            keyword=c.keyword,
            caller_phone=c.caller_phone,
            rep_score=c.score.rep_score if c.score else None,
            lead_score=c.score.lead_score if c.score else None,
            rep_name=rep_name,
            conversion_status=c.conversion.status if c.conversion else None,
        ))
    return results


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope_filter=Depends(get_call_scope_filter),
):
    base_query = scope_filter(db.query(Call), Call, db)
    scoped_ids = [c.id for c in base_query.all()]

    if not scoped_ids:
        return DashboardStats(
            total_calls=0, completed_calls=0,
            avg_rep_score=None, avg_lead_score=None,
            recent_calls=[],
        )

    total = len(scoped_ids)
    completed = base_query.filter(Call.status == "completed").count()

    avg_rep = db.query(func.avg(CallScore.rep_score)).filter(
        CallScore.call_id.in_(scoped_ids)
    ).scalar()
    avg_lead = db.query(func.avg(CallScore.lead_score)).filter(
        CallScore.call_id.in_(scoped_ids)
    ).scalar()

    recent = base_query.order_by(Call.call_date.desc().nullslast()).limit(5).all()
    recent_summaries = []
    for c in recent:
        rep_name = None
        if c.rep_id:
            rep = db.query(User).filter(User.id == c.rep_id).first()
            rep_name = rep.name if rep else None
        recent_summaries.append(CallSummary(
            id=c.id, call_date=c.call_date, duration=c.duration,
            status=c.status, source_type=c.source_type,
            campaign_name=c.campaign_name, keyword=c.keyword,
            caller_phone=c.caller_phone,
            rep_score=c.score.rep_score if c.score else None,
            lead_score=c.score.lead_score if c.score else None,
            rep_name=rep_name,
            conversion_status=c.conversion.status if c.conversion else None,
        ))

    return DashboardStats(
        total_calls=total, completed_calls=completed,
        avg_rep_score=round(avg_rep, 2) if avg_rep is not None else None,
        avg_lead_score=round(avg_lead, 2) if avg_lead is not None else None,
        recent_calls=recent_summaries,
    )


@router.get("/{call_id}", response_model=CallDetail)
def get_call(
    call_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope_filter=Depends(get_call_scope_filter),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    _check_call_access(call, scope_filter, db)
    log_audit(db, current_user, "view_call", request, "call", call_id)

    rep_name = None
    if call.rep_id:
        rep = db.query(User).filter(User.id == call.rep_id).first()
        rep_name = rep.name if rep else None

    return CallDetail(
        id=call.id,
        created_at=call.created_at,
        ctm_call_id=call.ctm_call_id,
        caller_phone=call.caller_phone,
        receiving_number=call.receiving_number,
        duration=call.duration,
        call_date=call.call_date,
        campaign_name=call.campaign_name,
        keyword=call.keyword,
        landing_page_url=call.landing_page_url,
        gclid=call.gclid,
        audio_filename=call.audio_filename,
        status=call.status,
        source_type=call.source_type,
        error_message=call.error_message,
        rep_id=call.rep_id,
        rep_name=rep_name,
        transcript=call.transcript,
        score=call.score,
        conversion=call.conversion,
    )


@router.get("/{call_id}/status", response_model=CallStatusResponse)
def get_call_status(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope_filter=Depends(get_call_scope_filter),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    _check_call_access(call, scope_filter, db)
    return CallStatusResponse(id=call.id, status=call.status, error_message=call.error_message)


@router.delete("/{call_id}")
def delete_call(
    call_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin),
    scope_filter=Depends(get_call_scope_filter),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    _check_call_access(call, scope_filter, db)

    if call.audio_filename:
        audio_path = STORAGE_DIR / call.audio_filename
        if audio_path.exists():
            audio_path.unlink()
        wav_path = audio_path.with_suffix(".wav")
        if wav_path.exists() and wav_path != audio_path:
            wav_path.unlink()

    log_audit(db, current_user, "delete_call", request, "call", call_id)
    db.delete(call)
    db.commit()
    return {"detail": "Call deleted"}


@router.get("/{call_id}/scores", response_model=CallScoreResponse)
def get_call_scores(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope_filter=Depends(get_call_scope_filter),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    _check_call_access(call, scope_filter, db)
    if not call.score:
        raise HTTPException(status_code=404, detail="Scores not available")
    return call.score


@router.patch("/{call_id}/assign")
def assign_call(
    call_id: int,
    req: CallAssignRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor_or_admin),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    rep = db.query(User).filter(User.id == req.rep_id).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Rep not found")

    call.rep_id = req.rep_id
    log_audit(db, current_user, "assign_call", request, "call", call_id,
              details={"rep_id": req.rep_id})
    db.commit()
    return {"detail": "Call assigned", "rep_id": req.rep_id}

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db, Call, CallScore, ConversionStatus, User
from models.schemas import ConversionStatusResponse
from dependencies import get_current_user, require_admin
from services.google_ads import upload_conversion
from services.audit import log_audit

router = APIRouter(prefix="/api/conversions", tags=["conversions"])


@router.post("/send/{call_id}", response_model=ConversionStatusResponse)
def send_conversion(
    call_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Manually trigger (or retry) a conversion upload for a call."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if not call.gclid:
        raise HTTPException(status_code=400, detail="Call has no GCLID — cannot send conversion")

    score = db.query(CallScore).filter(CallScore.call_id == call_id).first()
    lead_score = score.lead_score if score else None

    if lead_score is None:
        raise HTTPException(status_code=400, detail="Call has no lead score — cannot send conversion")

    # Remove existing conversion record if retrying
    existing = db.query(ConversionStatus).filter(ConversionStatus.call_id == call_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    result = upload_conversion(
        gclid=call.gclid,
        conversion_value=lead_score,
        conversion_time=call.call_date or datetime.now(timezone.utc),
    )

    conv = ConversionStatus(
        call_id=call_id,
        gclid=call.gclid,
        lead_score=lead_score,
        status=result["status"],
        error_message=result["error"],
        sent_at=datetime.now(timezone.utc) if "sent" in result["status"] else None,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    log_audit(db, current_user, "conversion_sent", request, "call", call_id)

    return conv


@router.get("/status", response_model=list[ConversionStatusResponse])
def list_conversions(
    status: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List conversion statuses, optionally filtered by status."""
    query = db.query(ConversionStatus).order_by(ConversionStatus.id.desc())
    if status:
        query = query.filter(ConversionStatus.status == status)
    return query.all()

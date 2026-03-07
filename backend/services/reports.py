"""Reports query logic — trends, campaigns, reps."""

from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Call, CallScore, ConversionStatus, User


def _round_or_none(val, digits=2):
    return round(val, digits) if val is not None else None


def get_scoped_call_ids(db: Session, scope_filter, start_date=None, end_date=None):
    """Return list of call IDs that pass scope + date filters."""
    query = scope_filter(db.query(Call), Call, db)
    query = query.filter(Call.status == "completed")
    if start_date:
        query = query.filter(Call.call_date >= start_date)
    if end_date:
        query = query.filter(Call.call_date < end_date + timedelta(days=1))
    return [c.id for c in query.all()], query


def compute_trends(db: Session, scope_filter, current_user, period="weekly",
                   start_date=None, end_date=None, rep_id=None):
    """Compute time-bucketed trends for calls."""
    if not end_date:
        end_date = datetime.now(timezone.utc).date()
    if not start_date:
        start_date = end_date - timedelta(days=90)

    call_ids, base_query = get_scoped_call_ids(db, scope_filter, start_date, end_date)
    if rep_id:
        call_ids = [
            c.id for c in base_query.filter(Call.rep_id == rep_id).all()
        ]

    bucket_days = 7 if period == "weekly" else 30
    buckets = []
    cursor = start_date
    while cursor <= end_date:
        bucket_end = cursor + timedelta(days=bucket_days - 1)
        if bucket_end > end_date:
            bucket_end = end_date

        bucket_call_ids = [
            c.id for c in db.query(Call).filter(
                Call.id.in_(call_ids),
                Call.call_date >= datetime(cursor.year, cursor.month, cursor.day, tzinfo=timezone.utc),
                Call.call_date < datetime(bucket_end.year, bucket_end.month, bucket_end.day, tzinfo=timezone.utc) + timedelta(days=1),
            ).all()
        ] if call_ids else []

        avg_rep = db.query(func.avg(CallScore.rep_score)).filter(
            CallScore.call_id.in_(bucket_call_ids)).scalar() if bucket_call_ids else None
        avg_lead = db.query(func.avg(CallScore.lead_score)).filter(
            CallScore.call_id.in_(bucket_call_ids)).scalar() if bucket_call_ids else None

        buckets.append({
            "start_date": cursor.isoformat(),
            "end_date": bucket_end.isoformat(),
            "call_count": len(bucket_call_ids),
            "avg_rep_score": _round_or_none(avg_rep),
            "avg_lead_score": _round_or_none(avg_lead),
        })
        cursor += timedelta(days=bucket_days)

    return {"period": period, "buckets": buckets}


def compute_campaigns(db: Session, scope_filter, start_date=None, end_date=None):
    """Campaign performance — avg scores, call volume, conversions."""
    call_ids, _ = get_scoped_call_ids(db, scope_filter, start_date, end_date)
    if not call_ids:
        return []

    campaigns = db.query(Call.campaign_name).filter(
        Call.id.in_(call_ids), Call.campaign_name.isnot(None)
    ).distinct().all()

    results = []
    for (campaign_name,) in campaigns:
        camp_call_ids = [
            c.id for c in db.query(Call).filter(
                Call.id.in_(call_ids), Call.campaign_name == campaign_name
            ).all()
        ]
        avg_lead = db.query(func.avg(CallScore.lead_score)).filter(
            CallScore.call_id.in_(camp_call_ids)).scalar()
        avg_rep = db.query(func.avg(CallScore.rep_score)).filter(
            CallScore.call_id.in_(camp_call_ids)).scalar()
        conversions_sent = db.query(ConversionStatus).filter(
            ConversionStatus.call_id.in_(camp_call_ids),
            ConversionStatus.status == "sent"
        ).count()

        results.append({
            "campaign_name": campaign_name,
            "call_count": len(camp_call_ids),
            "avg_lead_score": _round_or_none(avg_lead),
            "avg_rep_score": _round_or_none(avg_rep),
            "total_conversions_sent": conversions_sent,
        })

    results.sort(key=lambda x: x["call_count"], reverse=True)
    return results


def compute_reps(db: Session, scope_filter, start_date=None, end_date=None):
    """Rep performance — avg rep scores per rep."""
    call_ids, _ = get_scoped_call_ids(db, scope_filter, start_date, end_date)
    if not call_ids:
        return []

    rep_ids = db.query(Call.rep_id).filter(
        Call.id.in_(call_ids), Call.rep_id.isnot(None)
    ).distinct().all()

    results = []
    for (rid,) in rep_ids:
        user = db.query(User).filter(User.id == rid).first()
        if not user:
            continue
        rep_call_ids = [
            c.id for c in db.query(Call).filter(
                Call.id.in_(call_ids), Call.rep_id == rid
            ).all()
        ]
        avg_rep = db.query(func.avg(CallScore.rep_score)).filter(
            CallScore.call_id.in_(rep_call_ids)).scalar()

        results.append({
            "rep_id": rid,
            "rep_name": user.name,
            "call_count": len(rep_call_ids),
            "avg_rep_score": _round_or_none(avg_rep),
        })

    results.sort(key=lambda x: x["avg_rep_score"] or 0, reverse=True)
    return results


def get_calls_for_export(db: Session, scope_filter, start_date=None, end_date=None):
    """Return flat list of call data for CSV/PDF export."""
    call_ids, _ = get_scoped_call_ids(db, scope_filter, start_date, end_date)
    calls = db.query(Call).filter(Call.id.in_(call_ids)).order_by(Call.call_date.desc().nullslast()).all()

    rows = []
    for c in calls:
        rep = db.query(User).filter(User.id == c.rep_id).first() if c.rep_id else None
        rows.append({
            "id": c.id,
            "call_date": c.call_date.strftime("%Y-%m-%d %H:%M") if c.call_date else "",
            "duration_sec": round(c.duration, 1) if c.duration else "",
            "campaign": c.campaign_name or "",
            "keyword": c.keyword or "",
            "caller_phone": c.caller_phone or "",
            "rep": rep.name if rep else "",
            "rep_score": round(c.score.rep_score, 1) if c.score and c.score.rep_score is not None else "",
            "lead_score": round(c.score.lead_score, 1) if c.score and c.score.lead_score is not None else "",
            "status": c.status,
            "conversion": c.conversion.status if c.conversion else "",
        })
    return rows

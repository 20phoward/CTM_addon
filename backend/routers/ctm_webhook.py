import uuid
import logging

import httpx
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi import Depends
from datetime import datetime, timezone

from database import get_db, Call, SessionLocal
from config import CTM_WEBHOOK_SECRET, STORAGE_DIR
from services.pipeline import process_call

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ctm", tags=["ctm"])


def download_ctm_audio(recording_url: str, filename: str) -> str:
    """Download audio file from CTM recording URL. Returns filename."""
    dest = STORAGE_DIR / filename
    with httpx.Client(timeout=120) as client:
        resp = client.get(recording_url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    logger.info("Downloaded CTM recording to %s (%d bytes)", filename, len(resp.content))
    return filename


def _run_pipeline(call_id: int):
    """Run the processing pipeline in a background thread."""
    db = SessionLocal()
    try:
        process_call(call_id, db)
    finally:
        db.close()


@router.post("/webhook")
def ctm_webhook(
    payload: dict,
    background_tasks: BackgroundTasks,
    x_ctm_secret: str = Header(None, alias="X-CTM-Secret"),
    db: Session = Depends(get_db),
):
    """Receive CTM call-ended webhook."""
    if not CTM_WEBHOOK_SECRET or x_ctm_secret != CTM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    ctm_call_id = payload.get("id")
    recording_url = payload.get("recording_url")

    if not recording_url:
        raise HTTPException(status_code=400, detail="No recording_url provided")

    if ctm_call_id:
        existing = db.query(Call).filter(Call.ctm_call_id == ctm_call_id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Call already processed")

    ext = ".mp3"
    if recording_url:
        url_path = recording_url.rsplit("?", 1)[0]
        if "." in url_path.split("/")[-1]:
            ext = "." + url_path.split("/")[-1].rsplit(".", 1)[1]

    filename = f"{ctm_call_id or uuid.uuid4().hex}{ext}"

    try:
        download_ctm_audio(recording_url, filename)
    except Exception as e:
        logger.exception("Failed to download CTM recording: %s", recording_url)
        raise HTTPException(status_code=502, detail=f"Failed to download recording: {e}")

    call = Call(
        ctm_call_id=ctm_call_id,
        caller_phone=payload.get("caller_number"),
        receiving_number=payload.get("receiving_number"),
        duration=float(payload["duration"]) if payload.get("duration") else None,
        call_date=datetime.now(timezone.utc),
        campaign_name=payload.get("campaign_name"),
        keyword=payload.get("keyword"),
        landing_page_url=payload.get("landing_page"),
        gclid=payload.get("gclid"),
        audio_filename=filename,
        audio_url=recording_url,
        source_type="webhook",
        status="pending",
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    logger.info("CTM webhook: created call %d (ctm_id=%s)", call.id, ctm_call_id)
    background_tasks.add_task(_run_pipeline, call.id)

    return {"id": call.id, "ctm_call_id": ctm_call_id, "status": call.status}

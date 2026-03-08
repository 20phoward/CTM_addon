# Phase 4: Google Ads Offline Conversion Upload — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** After scoring a call, automatically send Lead Score as an offline conversion to Google Ads via GCLID, with mock/dry-run mode for testing.

**Architecture:** New `services/google_ads.py` handles conversion upload (real or mock). Pipeline calls it after scoring if GCLID present. New `routers/conversions.py` provides admin endpoints for manual send/retry and status listing. Config gets `GOOGLE_ADS_DRY_RUN` and `GOOGLE_ADS_CONVERSION_ACTION` env vars.

**Tech Stack:** Python, FastAPI, SQLAlchemy, google-ads (Python client, deferred until real mode needed)

---

### Task 1: Add Config Vars and Google Ads Service (Mock Mode)

**Files:**
- Modify: `backend/config.py`
- Create: `backend/services/google_ads.py`
- Create: `backend/tests/test_google_ads.py`

**Step 1: Add new config vars to `backend/config.py`**

Add after the existing Google Ads config block (after line 31):
```python
GOOGLE_ADS_DRY_RUN = os.getenv("GOOGLE_ADS_DRY_RUN", "true").lower() in ("true", "1", "yes")
GOOGLE_ADS_CONVERSION_ACTION = os.getenv("GOOGLE_ADS_CONVERSION_ACTION", "")
```

**Step 2: Write tests for `backend/tests/test_google_ads.py`**

```python
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from services.google_ads import upload_conversion, is_dry_run


def test_is_dry_run_when_no_customer_id():
    with patch("services.google_ads.GOOGLE_ADS_CUSTOMER_ID", ""):
        with patch("services.google_ads.GOOGLE_ADS_DRY_RUN", False):
            assert is_dry_run() is True


def test_is_dry_run_when_flag_set():
    with patch("services.google_ads.GOOGLE_ADS_CUSTOMER_ID", "123-456-7890"):
        with patch("services.google_ads.GOOGLE_ADS_DRY_RUN", True):
            assert is_dry_run() is True


def test_is_not_dry_run_when_configured():
    with patch("services.google_ads.GOOGLE_ADS_CUSTOMER_ID", "123-456-7890"):
        with patch("services.google_ads.GOOGLE_ADS_DRY_RUN", False):
            assert is_dry_run() is False


def test_upload_conversion_dry_run():
    with patch("services.google_ads.is_dry_run", return_value=True):
        result = upload_conversion(
            gclid="test-gclid-abc",
            conversion_value=8.5,
            conversion_time=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
        )
    assert result["status"] == "sent (dry_run)"
    assert result["gclid"] == "test-gclid-abc"
    assert result["conversion_value"] == 8.5
    assert result["error"] is None


def test_upload_conversion_missing_gclid():
    result = upload_conversion(
        gclid="",
        conversion_value=7.0,
        conversion_time=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result["status"] == "failed"
    assert "gclid" in result["error"].lower()


def test_upload_conversion_missing_value():
    result = upload_conversion(
        gclid="test-gclid",
        conversion_value=None,
        conversion_time=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result["status"] == "failed"
    assert "value" in result["error"].lower()
```

**Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_google_ads.py -v`
Expected: FAIL (module not found)

**Step 4: Create `backend/services/google_ads.py`**

```python
import logging
from datetime import datetime

from config import (
    GOOGLE_ADS_CUSTOMER_ID,
    GOOGLE_ADS_DRY_RUN,
    GOOGLE_ADS_CONVERSION_ACTION,
    GOOGLE_ADS_DEVELOPER_TOKEN,
    GOOGLE_ADS_CLIENT_ID,
    GOOGLE_ADS_CLIENT_SECRET,
    GOOGLE_ADS_REFRESH_TOKEN,
)

logger = logging.getLogger(__name__)


def is_dry_run() -> bool:
    """Check if we should use dry-run mode (no actual API calls)."""
    if not GOOGLE_ADS_CUSTOMER_ID:
        return True
    return GOOGLE_ADS_DRY_RUN


def upload_conversion(
    gclid: str,
    conversion_value: float | None,
    conversion_time: datetime,
) -> dict:
    """Upload an offline conversion to Google Ads.

    Returns dict with keys: status, gclid, conversion_value, error
    """
    if not gclid:
        return {
            "status": "failed",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": "Missing GCLID — cannot upload conversion",
        }

    if conversion_value is None:
        return {
            "status": "failed",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": "Missing conversion value — lead score not available",
        }

    if is_dry_run():
        logger.info(
            "DRY RUN: Would upload conversion gclid=%s value=%.1f action=%s customer=%s",
            gclid, conversion_value, GOOGLE_ADS_CONVERSION_ACTION, GOOGLE_ADS_CUSTOMER_ID,
        )
        return {
            "status": "sent (dry_run)",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": None,
        }

    # Real Google Ads API upload
    try:
        _upload_to_google_ads(gclid, conversion_value, conversion_time)
        return {
            "status": "sent",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": None,
        }
    except Exception as e:
        logger.exception("Google Ads conversion upload failed for gclid=%s", gclid)
        return {
            "status": "failed",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": str(e),
        }


def _upload_to_google_ads(gclid: str, conversion_value: float, conversion_time: datetime):
    """Call Google Ads API to upload offline conversion.

    Requires google-ads package. Will raise ImportError if not installed.
    """
    from google.ads.googleads.client import GoogleAdsClient  # type: ignore

    credentials = {
        "developer_token": GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id": GOOGLE_ADS_CLIENT_ID,
        "client_secret": GOOGLE_ADS_CLIENT_SECRET,
        "refresh_token": GOOGLE_ADS_REFRESH_TOKEN,
        "use_proto_plus": True,
    }
    client = GoogleAdsClient.load_from_dict(credentials)
    service = client.get_service("ConversionUploadService")

    click_conversion = client.get_type("ClickConversion")
    click_conversion.gclid = gclid
    click_conversion.conversion_action = (
        f"customers/{GOOGLE_ADS_CUSTOMER_ID}/conversionActions/{GOOGLE_ADS_CONVERSION_ACTION}"
    )
    click_conversion.conversion_value = conversion_value
    click_conversion.conversion_date_time = conversion_time.strftime("%Y-%m-%d %H:%M:%S%z")
    click_conversion.currency_code = "USD"

    response = service.upload_click_conversions(
        customer_id=GOOGLE_ADS_CUSTOMER_ID.replace("-", ""),
        conversions=[click_conversion],
    )

    if response.partial_failure_error:
        raise RuntimeError(f"Partial failure: {response.partial_failure_error.message}")

    logger.info("Conversion uploaded successfully for gclid=%s", gclid)
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_google_ads.py -v`
Expected: 6 tests PASS

**Step 6: Commit**

```bash
git add backend/config.py backend/services/google_ads.py backend/tests/test_google_ads.py
git commit -m "feat: add Google Ads conversion service with dry-run mode"
```

---

### Task 2: Integrate Conversion Upload into Pipeline

**Files:**
- Modify: `backend/services/pipeline.py`
- Modify: `backend/tests/test_pipeline.py`

**Step 1: Add conversion tests to `backend/tests/test_pipeline.py`**

Add these tests (append to the existing test file):

```python
def test_pipeline_creates_conversion_when_gclid_present(tmp_path, db):
    """Pipeline should create ConversionStatus after scoring if GCLID exists."""
    from database import ConversionStatus

    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake-wav-data")

    call = Call(
        source_type="ctm_webhook",
        audio_filename=str(audio),
        status="pending",
        gclid="test-gclid-pipeline",
    )
    db.add(call)
    db.commit()

    with patch("services.pipeline.STORAGE_DIR", tmp_path), \
         patch("services.pipeline.convert_to_wav", return_value=audio), \
         patch("services.pipeline.transcribe_audio", return_value={
             "full_text": "Hello", "segments": [], "duration": 30.0
         }), \
         patch("services.pipeline.score_call", return_value={
             "rep_score": 7.0, "lead_score": 8.5,
             "rep_tone": 7.0, "rep_steering": 7.0, "rep_service": 7.0, "rep_reasoning": "Good",
             "lead_service_match": 9.0, "lead_insurance": 8.0, "lead_intent": 9.0, "lead_reasoning": "Strong",
         }), \
         patch("services.pipeline.send_conversion") as mock_send:
        process_call(call.id, db)

    mock_send.assert_called_once()
    conv = db.query(ConversionStatus).filter(ConversionStatus.call_id == call.id).first()
    assert conv is not None
    assert conv.gclid == "test-gclid-pipeline"
    assert conv.lead_score == 8.5
    assert conv.status == "pending"


def test_pipeline_skips_conversion_when_no_gclid(tmp_path, db):
    """Pipeline should not create ConversionStatus if no GCLID."""
    from database import ConversionStatus

    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake-wav-data")

    call = Call(
        source_type="manual_upload",
        audio_filename=str(audio),
        status="pending",
    )
    db.add(call)
    db.commit()

    with patch("services.pipeline.STORAGE_DIR", tmp_path), \
         patch("services.pipeline.convert_to_wav", return_value=audio), \
         patch("services.pipeline.transcribe_audio", return_value={
             "full_text": "Hello", "segments": [], "duration": 30.0
         }), \
         patch("services.pipeline.score_call", return_value={
             "rep_score": 7.0, "lead_score": 8.5,
             "rep_tone": 7.0, "rep_steering": 7.0, "rep_service": 7.0, "rep_reasoning": "Good",
             "lead_service_match": 9.0, "lead_insurance": 8.0, "lead_intent": 9.0, "lead_reasoning": "Strong",
         }):
        process_call(call.id, db)

    conv = db.query(ConversionStatus).filter(ConversionStatus.call_id == call.id).first()
    assert conv is None
```

Note: These tests need the existing imports from test_pipeline.py (`from unittest.mock import patch`, `from services.pipeline import process_call`, `from database import Call`). Check the existing file for the fixture setup.

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v -k "conversion"`
Expected: FAIL (send_conversion not found or ConversionStatus not created)

**Step 3: Update `backend/services/pipeline.py`**

Add the conversion step after scoring. The updated file:

```python
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from config import STORAGE_DIR
from database import Call, Transcript, CallScore, ConversionStatus
from services.transcription import transcribe_audio
from services.scoring import score_call
from services.google_ads import upload_conversion

logger = logging.getLogger(__name__)


def convert_to_wav(input_path: Path) -> Path:
    """Convert any audio file to 16kHz mono WAV for Whisper."""
    wav_path = input_path.with_suffix(".wav")
    if input_path.suffix.lower() == ".wav":
        return input_path
    logger.info("Converting %s -> %s", input_path.name, wav_path.name)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            str(wav_path),
        ],
        capture_output=True,
        check=True,
    )
    return wav_path


def send_conversion(call: Call, lead_score: float, db: Session):
    """Upload conversion to Google Ads if GCLID present."""
    if not call.gclid:
        return

    conv = ConversionStatus(
        call_id=call.id,
        gclid=call.gclid,
        lead_score=lead_score,
        status="pending",
    )
    db.add(conv)
    db.commit()

    result = upload_conversion(
        gclid=call.gclid,
        conversion_value=lead_score,
        conversion_time=call.call_date or datetime.now(timezone.utc),
    )

    conv.status = result["status"]
    conv.error_message = result["error"]
    if "sent" in result["status"]:
        conv.sent_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("Conversion for call %d: %s", call.id, result["status"])


def process_call(call_id: int, db: Session):
    """Full processing pipeline: transcode -> transcribe -> score -> store -> convert."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        logger.error("Call %d not found", call_id)
        return

    try:
        call.status = "processing"
        db.commit()

        audio_path = STORAGE_DIR / call.audio_filename
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Transcode
        wav_path = convert_to_wav(audio_path)

        # Transcribe
        logger.info("Transcribing call %d", call_id)
        tx_result = transcribe_audio(wav_path)

        transcript = Transcript(
            call_id=call_id,
            full_text=tx_result["full_text"],
            segments=tx_result["segments"],
        )
        db.add(transcript)
        call.duration = tx_result["duration"]
        db.commit()

        # Score with Claude AI
        logger.info("Scoring call %d", call_id)
        call_metadata = {
            "duration": call.duration,
            "campaign_name": call.campaign_name,
            "keyword": call.keyword,
            "landing_page_url": call.landing_page_url,
        }
        scores = score_call(tx_result["full_text"], tx_result["segments"], call_metadata)

        if scores:
            call_score = CallScore(call_id=call_id, **scores)
        else:
            call_score = CallScore(call_id=call_id)
        db.add(call_score)

        call.status = "completed"
        db.commit()

        # Send conversion to Google Ads (if GCLID present and lead score exists)
        lead_score = scores.get("lead_score") if scores else None
        if call.gclid and lead_score is not None:
            send_conversion(call, lead_score, db)

        logger.info("Call %d processing completed", call_id)

    except Exception as e:
        logger.exception("Processing failed for call %d", call_id)
        call.status = "failed"
        call.error_message = str(e)
        db.commit()
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: All pipeline tests PASS

**Step 5: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: integrate Google Ads conversion upload into pipeline"
```

---

### Task 3: Add Conversions Router

**Files:**
- Create: `backend/routers/conversions.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_conversions.py`

**Step 1: Write tests for `backend/tests/test_conversions.py`**

```python
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal, Call, CallScore, ConversionStatus


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    client.post("/api/auth/register", json={
        "email": "convadmin@test.com", "password": "Admin123!", "name": "Conv Admin"
    })
    resp = client.post("/api/auth/login", json={
        "email": "convadmin@test.com", "password": "Admin123!"
    })
    return resp.json()["access_token"]


@pytest.fixture
def rep_token(client, admin_token):
    client.post("/api/auth/register", json={
        "email": "convrep@test.com", "password": "Rep12345!", "name": "Conv Rep"
    })
    resp = client.post("/api/auth/login", json={
        "email": "convrep@test.com", "password": "Rep12345!"
    })
    return resp.json()["access_token"]


@pytest.fixture
def scored_call_with_gclid(admin_token):
    db = SessionLocal()
    try:
        call = Call(
            source_type="ctm_webhook",
            audio_filename="test.wav",
            status="completed",
            gclid="test-gclid-conv",
            call_date=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        score = CallScore(call_id=call.id, lead_score=8.0, rep_score=7.0)
        db.add(score)
        db.commit()

        return call.id
    finally:
        db.close()


def test_send_conversion_creates_status(client, admin_token, scored_call_with_gclid):
    with patch("routers.conversions.upload_conversion", return_value={
        "status": "sent (dry_run)", "gclid": "test-gclid-conv",
        "conversion_value": 8.0, "error": None,
    }):
        resp = client.post(
            f"/api/conversions/send/{scored_call_with_gclid}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent (dry_run)"
    assert data["gclid"] == "test-gclid-conv"


def test_send_conversion_requires_admin(client, rep_token, scored_call_with_gclid):
    resp = client.post(
        f"/api/conversions/send/{scored_call_with_gclid}",
        headers={"Authorization": f"Bearer {rep_token}"},
    )
    assert resp.status_code == 403


def test_send_conversion_404_for_missing_call(client, admin_token):
    resp = client.post(
        "/api/conversions/send/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_send_conversion_400_no_gclid(client, admin_token):
    db = SessionLocal()
    try:
        call = Call(source_type="manual_upload", audio_filename="x.wav", status="completed")
        db.add(call)
        db.commit()
        db.refresh(call)
        call_id = call.id
    finally:
        db.close()

    resp = client.post(
        f"/api/conversions/send/{call_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "gclid" in resp.json()["detail"].lower()


def test_list_conversions(client, admin_token, scored_call_with_gclid):
    # Create a conversion record first
    db = SessionLocal()
    try:
        conv = ConversionStatus(
            call_id=scored_call_with_gclid,
            gclid="test-gclid-conv",
            lead_score=8.0,
            status="sent (dry_run)",
        )
        db.add(conv)
        db.commit()
    finally:
        db.close()

    resp = client.get(
        "/api/conversions/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["gclid"] == "test-gclid-conv"


def test_list_conversions_filter_by_status(client, admin_token, scored_call_with_gclid):
    db = SessionLocal()
    try:
        conv = ConversionStatus(
            call_id=scored_call_with_gclid,
            gclid="test-gclid-conv",
            lead_score=8.0,
            status="failed",
            error_message="test error",
        )
        db.add(conv)
        db.commit()
    finally:
        db.close()

    resp = client.get(
        "/api/conversions/status?status=failed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(c["status"] == "failed" for c in data)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_conversions.py -v`
Expected: FAIL (router not found)

**Step 3: Create `backend/routers/conversions.py`**

```python
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
```

**Step 4: Register the router in `backend/main.py`**

Add to imports (line 9):
```python
from routers import calls, upload, ctm_webhook, auth, users, teams, audit, reports, conversions
```

Add after line 32:
```python
app.include_router(conversions.router)
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_conversions.py -v`
Expected: 7 tests PASS

**Step 6: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS (67 existing + 6 google_ads + 2 pipeline + 7 conversions = ~82)

**Step 7: Commit**

```bash
git add backend/routers/conversions.py backend/tests/test_conversions.py backend/main.py
git commit -m "feat: add conversions router with manual send/retry and status listing"
```

---

### Task 4: Add google-ads to requirements.txt (Optional Dependency)

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add google-ads as optional dependency**

Add to the end of `backend/requirements.txt`:
```
# Google Ads (only needed when GOOGLE_ADS_DRY_RUN=false)
# google-ads>=24.0.0
```

Note: Commented out because it's not needed for dry-run mode. Uncomment when ready for live integration.

**Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "docs: note google-ads dependency in requirements.txt (commented, for live mode)"
```

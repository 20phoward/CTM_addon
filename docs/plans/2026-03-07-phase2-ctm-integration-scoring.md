# Phase 2: CTM Integration + Scoring Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the CTM webhook endpoint to receive call data, download audio from CTM, and score calls with Claude AI (Rep Score + Lead Score with sub-scores and reasoning).

**Architecture:** CTM sends a POST webhook when a call ends. Our app validates the shared secret, stores call metadata, downloads the recording, then runs the pipeline (transcode → transcribe → AI score → store). The scoring service sends the transcript + CTM metadata to Claude API and parses structured JSON output.

**Tech Stack:** FastAPI, httpx (audio download), Anthropic Claude API (Sonnet 4.6), Whisper (transcription)

---

### Task 1: Create the scoring service

**Files:**
- Create: `backend/services/scoring.py`
- Test: `backend/tests/test_scoring.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_scoring.py
import json
from unittest.mock import patch, MagicMock
from services.scoring import score_call, parse_scoring_response


def test_parse_scoring_response_valid():
    raw = json.dumps({
        "rep_score": 8, "rep_tone": 9, "rep_steering": 7, "rep_service": 8,
        "rep_reasoning": "Agent was professional and warm.",
        "lead_score": 7, "lead_service_match": 9, "lead_insurance": 5, "lead_intent": 7,
        "lead_reasoning": "Caller asked about inpatient rehab.",
    })
    result = parse_scoring_response(raw)
    assert result is not None
    assert result["rep_score"] == 8
    assert result["lead_score"] == 7
    assert result["rep_reasoning"] == "Agent was professional and warm."
    assert result["lead_insurance"] == 5


def test_parse_scoring_response_with_code_fences():
    raw = "```json\n" + json.dumps({
        "rep_score": 8, "rep_tone": 9, "rep_steering": 7, "rep_service": 8,
        "rep_reasoning": "Good.", "lead_score": 7, "lead_service_match": 9,
        "lead_insurance": 5, "lead_intent": 7, "lead_reasoning": "Strong.",
    }) + "\n```"
    result = parse_scoring_response(raw)
    assert result is not None
    assert result["rep_score"] == 8


def test_parse_scoring_response_invalid_json():
    result = parse_scoring_response("not json at all")
    assert result is None


def test_score_call_returns_scores():
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps({
        "rep_score": 8, "rep_tone": 9, "rep_steering": 7, "rep_service": 8,
        "rep_reasoning": "Good.", "lead_score": 7, "lead_service_match": 9,
        "lead_insurance": 5, "lead_intent": 7, "lead_reasoning": "Strong.",
    })

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("services.scoring.anthropic.Anthropic", return_value=mock_client):
        result = score_call(
            transcript_text="Hello, I need help with rehab.",
            segments=[{"start": 0.0, "end": 2.0, "text": "Hello, I need help with rehab."}],
            call_metadata={"duration": 120, "campaign_name": "Rehab Ads", "keyword": "inpatient rehab", "landing_page_url": "https://example.com/rehab"},
        )

    assert result is not None
    assert result["rep_score"] == 8
    assert result["lead_score"] == 7


def test_score_call_no_api_key():
    with patch("services.scoring.ANTHROPIC_API_KEY", ""):
        result = score_call(
            transcript_text="Hello",
            segments=[{"start": 0.0, "end": 1.0, "text": "Hello"}],
            call_metadata={},
        )
    assert result is None
```

**Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/test_scoring.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'services.scoring'`

**Step 3: Write the implementation**

```python
# backend/services/scoring.py
import json
import logging

import anthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

SCORING_PROMPT = """\
You are an expert call analyst for a behavioral health and rehabilitation facility. \
Analyze the following call transcript and score it on two independent dimensions.

<transcript>
{transcript}
</transcript>

<call_metadata>
Duration: {duration} seconds
Campaign: {campaign}
Keyword: {keyword}
Landing Page: {landing_page}
</call_metadata>

Produce TWO independent scores (0-10 scale) with sub-scores and reasoning.

**Rep Score** — How well did the representative handle the call?
- tone (0-10): Friendly, professional, empathetic
- steering (0-10): Guided conversation productively, stayed on track
- service (0-10): Addressed concerns, answered questions, offered clear next steps

**Lead Score** — How qualified is the caller as a prospect?
- service_match (0-10): Were they specifically looking for behavioral health / rehab services?
- insurance (0-10): Did they mention having private health insurance?
- intent (0-10): Actively seeking treatment vs. just browsing?

Score guide: 0-3 Poor, 4-5 Below average, 6-7 Average, 8-9 Good, 10 Exceptional.

Respond with ONLY valid JSON (no markdown, no code fences) in this exact schema:
{{
  "rep_score": <overall 0-10>,
  "rep_tone": <0-10>,
  "rep_steering": <0-10>,
  "rep_service": <0-10>,
  "rep_reasoning": "<2-3 sentences explaining the rep score>",
  "lead_score": <overall 0-10>,
  "lead_service_match": <0-10>,
  "lead_insurance": <0-10>,
  "lead_intent": <0-10>,
  "lead_reasoning": "<2-3 sentences explaining the lead score>"
}}
"""


def parse_scoring_response(raw: str) -> dict | None:
    """Parse Claude's JSON response into a structured dict."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse scoring response: %s", raw[:500])
        return None

    return {
        "rep_score": float(data.get("rep_score", 0)),
        "rep_tone": float(data.get("rep_tone", 0)),
        "rep_steering": float(data.get("rep_steering", 0)),
        "rep_service": float(data.get("rep_service", 0)),
        "rep_reasoning": data.get("rep_reasoning", ""),
        "lead_score": float(data.get("lead_score", 0)),
        "lead_service_match": float(data.get("lead_service_match", 0)),
        "lead_insurance": float(data.get("lead_insurance", 0)),
        "lead_intent": float(data.get("lead_intent", 0)),
        "lead_reasoning": data.get("lead_reasoning", ""),
    }


def score_call(transcript_text: str, segments: list[dict], call_metadata: dict) -> dict | None:
    """Send transcript + metadata to Claude for Rep + Lead scoring.

    Returns parsed dict with scores, or None if API key is missing.
    """
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — skipping scoring")
        return None

    lines = []
    for seg in segments:
        ts = f"[{seg['start']:.1f}s - {seg['end']:.1f}s]"
        speaker = f" ({seg['speaker']})" if seg.get("speaker") else ""
        lines.append(f"{ts}{speaker} {seg['text']}")
    formatted_transcript = "\n".join(lines)

    prompt = SCORING_PROMPT.format(
        transcript=formatted_transcript,
        duration=call_metadata.get("duration", "unknown"),
        campaign=call_metadata.get("campaign_name", "unknown"),
        keyword=call_metadata.get("keyword", "unknown"),
        landing_page=call_metadata.get("landing_page_url", "unknown"),
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    return parse_scoring_response(raw)
```

**Step 4: Run tests to verify they pass**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/test_scoring.py -v
```

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add backend/services/scoring.py backend/tests/test_scoring.py
git commit -m "feat: add AI scoring service (Rep + Lead scores via Claude API)"
```

---

### Task 2: Integrate scoring into pipeline

**Files:**
- Modify: `backend/services/pipeline.py`
- Modify: `backend/tests/test_pipeline.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_pipeline.py`:

```python
def test_pipeline_calls_scoring_service(db):
    call = Call(audio_filename="test.wav", status="pending",
                campaign_name="Rehab Ads", keyword="inpatient rehab",
                landing_page_url="https://example.com")
    db.add(call)
    db.commit()

    mock_tx = {
        "full_text": "Hello, I need help with rehab.",
        "segments": [{"start": 0.0, "end": 2.0, "text": "Hello, I need help with rehab."}],
        "duration": 120.0,
    }
    mock_scores = {
        "rep_score": 8.0, "rep_tone": 9.0, "rep_steering": 7.0, "rep_service": 8.0,
        "rep_reasoning": "Good call handling.",
        "lead_score": 7.0, "lead_service_match": 9.0, "lead_insurance": 5.0, "lead_intent": 7.0,
        "lead_reasoning": "Strong intent for treatment.",
    }

    mock_wav_path = MagicMock(spec=Path)
    mock_wav_path.exists.return_value = True

    with patch("services.pipeline.convert_to_wav", return_value=mock_wav_path), \
         patch("services.pipeline.transcribe_audio", return_value=mock_tx), \
         patch("services.pipeline.score_call", return_value=mock_scores) as mock_score, \
         patch("services.pipeline.STORAGE_DIR", new_callable=lambda: MagicMock(spec=Path)) as mock_dir:

        mock_dir.__truediv__ = MagicMock(return_value=mock_wav_path)

        from services.pipeline import process_call
        process_call(call.id, db)

    db.refresh(call)
    assert call.status == "completed"
    assert call.score is not None
    assert call.score.rep_score == 8.0
    assert call.score.lead_score == 7.0
    assert call.score.rep_reasoning == "Good call handling."
    assert call.score.lead_reasoning == "Strong intent for treatment."
    mock_score.assert_called_once()


def test_pipeline_handles_scoring_failure(db):
    call = Call(audio_filename="test.wav", status="pending")
    db.add(call)
    db.commit()

    mock_tx = {
        "full_text": "Hello",
        "segments": [{"start": 0.0, "end": 1.0, "text": "Hello"}],
        "duration": 1.0,
    }

    mock_wav_path = MagicMock(spec=Path)
    mock_wav_path.exists.return_value = True

    with patch("services.pipeline.convert_to_wav", return_value=mock_wav_path), \
         patch("services.pipeline.transcribe_audio", return_value=mock_tx), \
         patch("services.pipeline.score_call", return_value=None), \
         patch("services.pipeline.STORAGE_DIR", new_callable=lambda: MagicMock(spec=Path)) as mock_dir:

        mock_dir.__truediv__ = MagicMock(return_value=mock_wav_path)

        from services.pipeline import process_call
        process_call(call.id, db)

    db.refresh(call)
    assert call.status == "completed"
    assert call.score is not None
    # Score exists but has no values (placeholder)
    assert call.score.rep_score is None
```

**Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/test_pipeline.py -v
```

Expected: FAIL — `score_call` not imported in pipeline.

**Step 3: Update pipeline.py to use scoring service**

Replace `backend/services/pipeline.py` with:

```python
import logging
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from config import STORAGE_DIR
from database import Call, Transcript, CallScore
from services.transcription import transcribe_audio
from services.scoring import score_call

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


def process_call(call_id: int, db: Session):
    """Full processing pipeline: transcode -> transcribe -> score -> store."""
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
        logger.info("Call %d processing completed", call_id)

    except Exception as e:
        logger.exception("Processing failed for call %d", call_id)
        call.status = "failed"
        call.error_message = str(e)
        db.commit()
```

**Step 4: Run tests to verify they pass**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/test_pipeline.py tests/test_scoring.py -v
```

Expected: All tests PASS.

**Step 5: Run full test suite**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/ -v
```

Expected: All 61+ tests PASS.

**Step 6: Commit**

```bash
git add backend/services/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: integrate AI scoring service into pipeline"
```

---

### Task 3: Create CTM webhook router with audio download

**Files:**
- Create: `backend/routers/ctm_webhook.py`
- Create: `backend/tests/test_ctm_webhook.py`

**Step 1: Write the failing tests**

```python
# backend/tests/test_ctm_webhook.py
from unittest.mock import patch, MagicMock, AsyncMock
from database import Call


def test_webhook_missing_secret(client):
    resp = client.post("/api/ctm/webhook", json={"id": "123"})
    assert resp.status_code == 403


def test_webhook_invalid_secret(client):
    resp = client.post("/api/ctm/webhook", json={"id": "123"},
                       headers={"X-CTM-Secret": "wrong-secret"})
    assert resp.status_code == 403


def test_webhook_creates_call(client, db):
    payload = {
        "id": "ctm-call-456",
        "caller_number": "+15551234567",
        "tracking_number": "+15559876543",
        "receiving_number": "+15551112222",
        "duration": 180,
        "recording_url": "https://ctm.example.com/recordings/456.mp3",
        "campaign_name": "Rehab Campaign",
        "keyword": "inpatient rehab",
        "landing_page": "https://example.com/rehab",
        "gclid": "test-gclid-abc123",
    }

    with patch("routers.ctm_webhook.CTM_WEBHOOK_SECRET", "test-secret"), \
         patch("routers.ctm_webhook.download_ctm_audio", return_value="ctm-call-456.mp3"):
        resp = client.post("/api/ctm/webhook", json=payload,
                           headers={"X-CTM-Secret": "test-secret"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["ctm_call_id"] == "ctm-call-456"
    assert data["status"] == "pending"

    call = db.query(Call).filter(Call.ctm_call_id == "ctm-call-456").first()
    assert call is not None
    assert call.campaign_name == "Rehab Campaign"
    assert call.gclid == "test-gclid-abc123"
    assert call.caller_phone == "+15551234567"


def test_webhook_duplicate_call_id(client, db):
    existing = Call(ctm_call_id="ctm-dup-789", status="completed")
    db.add(existing)
    db.commit()

    payload = {"id": "ctm-dup-789", "recording_url": "https://example.com/rec.mp3"}

    with patch("routers.ctm_webhook.CTM_WEBHOOK_SECRET", "test-secret"):
        resp = client.post("/api/ctm/webhook", json=payload,
                           headers={"X-CTM-Secret": "test-secret"})

    assert resp.status_code == 409


def test_webhook_no_recording_url(client, db):
    payload = {"id": "ctm-no-rec-999"}

    with patch("routers.ctm_webhook.CTM_WEBHOOK_SECRET", "test-secret"):
        resp = client.post("/api/ctm/webhook", json=payload,
                           headers={"X-CTM-Secret": "test-secret"})

    assert resp.status_code == 400
```

**Step 2: Run tests to verify they fail**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/test_ctm_webhook.py -v
```

Expected: FAIL — `No module named 'routers.ctm_webhook'`

**Step 3: Write the implementation**

```python
# backend/routers/ctm_webhook.py
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
    # Validate shared secret
    if not CTM_WEBHOOK_SECRET or x_ctm_secret != CTM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    ctm_call_id = payload.get("id")
    recording_url = payload.get("recording_url")

    if not recording_url:
        raise HTTPException(status_code=400, detail="No recording_url provided")

    # Check for duplicate
    if ctm_call_id:
        existing = db.query(Call).filter(Call.ctm_call_id == ctm_call_id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Call already processed")

    # Determine file extension from URL
    ext = ".mp3"
    if recording_url:
        url_path = recording_url.rsplit("?", 1)[0]
        if "." in url_path.split("/")[-1]:
            ext = "." + url_path.split("/")[-1].rsplit(".", 1)[1]

    filename = f"{ctm_call_id or uuid.uuid4().hex}{ext}"

    # Download audio
    try:
        download_ctm_audio(recording_url, filename)
    except Exception as e:
        logger.exception("Failed to download CTM recording: %s", recording_url)
        raise HTTPException(status_code=502, detail=f"Failed to download recording: {e}")

    # Create Call record
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

    # Kick off pipeline in background
    background_tasks.add_task(_run_pipeline, call.id)

    return {"id": call.id, "ctm_call_id": ctm_call_id, "status": call.status}
```

**Step 4: Register the router in main.py**

Add to `backend/main.py` imports:
```python
from routers import calls, upload, ctm_webhook, auth, users, teams, audit, reports
```

And add:
```python
app.include_router(ctm_webhook.router)
```

**Step 5: Run tests to verify they pass**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/test_ctm_webhook.py -v
```

Expected: All 5 tests PASS.

**Step 6: Run full test suite**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/ -v
```

Expected: All tests PASS (should be ~66).

**Step 7: Commit**

```bash
git add backend/routers/ctm_webhook.py backend/tests/test_ctm_webhook.py backend/main.py
git commit -m "feat: add CTM webhook endpoint with audio download and pipeline trigger"
```

---

### Task 4: Add httpx to requirements and add .env CTM_WEBHOOK_SECRET

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add httpx**

Add `httpx==0.27.2` to `backend/requirements.txt` (it's already installed as a test dep, but now it's a runtime dependency for CTM audio download).

**Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add httpx as runtime dependency for CTM audio download"
```

---

### Task 5: Final verification — run all tests

**Files:** None (verification only)

**Step 1: Run all tests**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/ -v
```

Expected: All tests PASS (~66 tests).

**Step 2: Verify app starts**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from main import app; print('OK')"
```

Expected: `OK`

**Step 3: Final commit if needed, then push**

```bash
git push
```

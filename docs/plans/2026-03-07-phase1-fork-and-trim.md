# Phase 1: Fork & Trim Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fork Call Monitor codebase into ctm-scorer, strip Twilio/review/tonality, update data models to the two-score system (Rep + Lead), and get all tests passing.

**Architecture:** Copy Call Monitor backend+frontend, delete Twilio and review code, replace TonalityResult/old CallScore with new CallScore model, replace tonality service with scoring service, update pipeline, update schemas, fix tests.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Whisper, Claude API, React 18, Vite, Tailwind CSS

---

### Task 1: Copy Call Monitor codebase

**Files:**
- Source: `/mnt/c/Users/ticta/workspace/call-monitor/`
- Destination: `/mnt/c/Users/ticta/workspace1/ctm-scorer/`

**Step 1: Copy backend and frontend directories**

```bash
cp -r /mnt/c/Users/ticta/workspace/call-monitor/backend /mnt/c/Users/ticta/workspace1/ctm-scorer/backend
cp -r /mnt/c/Users/ticta/workspace/call-monitor/frontend /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend
```

**Step 2: Remove files we won't need**

```bash
# Twilio-related backend files
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/routers/twilio_webhooks.py
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/services/twilio_service.py
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/services/tonality.py
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/tests/test_twilio_webhooks.py
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/tests/test_twilio_service.py
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/tests/test_tonality.py
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/tests/test_dial.py
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/tests/test_diarization.py

# Twilio/review frontend components
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend/src/components/CallDialer.jsx
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend/src/components/TonalityChart.jsx
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend/src/components/ReviewPanel.jsx
rm /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend/src/components/ScoreCard.jsx

# Old database files
rm -f /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/calls.db
rm -f /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/test*.db

# Old CLAUDE.md and docs (we already have our own)
rm -f /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/../ROADMAP.md
rm -f /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/../README.md
```

**Step 3: Verify directory structure**

```bash
find /mnt/c/Users/ticta/workspace1/ctm-scorer -type f -name "*.py" | sort
```

Expected: No twilio_webhooks.py, twilio_service.py, tonality.py, or test_twilio/test_dial/test_tonality files.

**Step 4: Commit**

Note: Git must be initialized from Windows PowerShell first. Skip this step until git is set up.

---

### Task 2: Update config.py — Remove Twilio, add CTM config

**Files:**
- Modify: `backend/config.py`

**Step 1: Write the new config.py**

Replace the entire file with:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "storage" / "audio")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'calls.db'}")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac"}
MAX_UPLOAD_SIZE_MB = 500

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# CTM Integration
CTM_WEBHOOK_SECRET = os.getenv("CTM_WEBHOOK_SECRET", "")

# Google Ads (Phase 4)
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
GOOGLE_ADS_CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
```

**Step 2: Verify no import errors**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "import config; print('OK')"
```

Expected: `OK`

---

### Task 3: Update database.py — New data models

**Files:**
- Modify: `backend/database.py`

**Step 1: Write the new database.py**

Replace the entire file. Key changes:
- `RoleEnum`: `worker` → `rep`
- `AuditAction`: remove `dial_call`, `recording_received`, `submit_review`, `update_review`; add `webhook_received`, `conversion_sent`
- `Call`: remove Twilio fields (`twilio_call_sid`, `call_direction`, `patient_phone`, `connection_mode`, `patient_name`), add CTM fields (`ctm_call_id`, `caller_phone`, `receiving_number`, `campaign_name`, `keyword`, `landing_page_url`, `gclid`, `audio_url`, `call_date`, `rep_id`)
- Remove `TonalityResult`, `Review`
- Replace `CallScore` with new two-score model
- Add `ConversionStatus`

```python
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, Column, Enum, Integer, String, Float, Text, DateTime, ForeignKey, JSON, create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import enum

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RoleEnum(str, enum.Enum):
    rep = "rep"
    supervisor = "supervisor"
    admin = "admin"


class AuditAction(str, enum.Enum):
    login = "login"
    logout = "logout"
    view_call = "view_call"
    view_transcript = "view_transcript"
    upload_call = "upload_call"
    delete_call = "delete_call"
    webhook_received = "webhook_received"
    conversion_sent = "conversion_sent"
    create_user = "create_user"
    update_role = "update_role"
    assign_call = "assign_call"


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    members = relationship("User", back_populates="team")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="rep")
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    password_changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    team = relationship("Team", back_populates="members")
    audit_logs = relationship("AuditLog", back_populates="user")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="audit_logs")


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # CTM metadata
    ctm_call_id = Column(String, nullable=True, unique=True)
    caller_phone = Column(String, nullable=True)
    receiving_number = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    call_date = Column(DateTime, nullable=True)

    # Attribution
    campaign_name = Column(String, nullable=True)
    keyword = Column(String, nullable=True)
    landing_page_url = Column(String, nullable=True)
    gclid = Column(String, nullable=True)

    # Audio
    audio_filename = Column(String, nullable=True)
    audio_url = Column(String, nullable=True)  # CTM recording URL

    # Processing
    status = Column(String, default="pending")  # pending/processing/completed/failed
    error_message = Column(Text, nullable=True)
    source_type = Column(String, default="webhook")  # webhook/manual_upload

    # Assignment
    rep_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    rep = relationship("User", foreign_keys=[rep_id])
    transcript = relationship("Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan")
    score = relationship("CallScore", back_populates="call", uselist=False, cascade="all, delete-orphan")
    conversion = relationship("ConversionStatus", back_populates="call", uselist=False, cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), unique=True)
    full_text = Column(Text, nullable=False)
    segments = Column(JSON, nullable=True)

    call = relationship("Call", back_populates="transcript")


class CallScore(Base):
    __tablename__ = "call_scores"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), unique=True)

    # Rep Score
    rep_score = Column(Float, nullable=True)
    rep_tone = Column(Float, nullable=True)
    rep_steering = Column(Float, nullable=True)
    rep_service = Column(Float, nullable=True)
    rep_reasoning = Column(Text, nullable=True)

    # Lead Score
    lead_score = Column(Float, nullable=True)
    lead_service_match = Column(Float, nullable=True)
    lead_insurance = Column(Float, nullable=True)
    lead_intent = Column(Float, nullable=True)
    lead_reasoning = Column(Text, nullable=True)

    call = relationship("Call", back_populates="score")


class ConversionStatus(Base):
    __tablename__ = "conversion_statuses"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), unique=True)
    gclid = Column(String, nullable=True)
    lead_score = Column(Float, nullable=True)
    status = Column(String, default="pending")  # pending/sent/failed
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    call = relationship("Call", back_populates="conversion")


def init_db():
    Base.metadata.create_all(bind=engine)
```

**Step 2: Verify no import errors**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from database import *; print('OK')"
```

Expected: `OK`

---

### Task 4: Update models/schemas.py — New Pydantic schemas

**Files:**
- Modify: `backend/models/schemas.py`

**Step 1: Write the new schemas.py**

Remove: `DialRequest`, `DialResponse`, `TwilioTokenResponse`, `TonalityResponse`, `SentimentPoint`, `KeyMoment`, `ReviewRequest`, `ReviewResponse`, old `CallScoreResponse`, old report schemas referencing sentiment/reviews.

Add: new `CallScoreResponse` (two-score), `ConversionStatusResponse`, `CallAssignRequest`, campaign/rep report schemas.

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# --- Auth ---

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "rep"
    team_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Users ---

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    team_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    role: Optional[str] = None
    team_id: Optional[int] = None


# --- Teams ---

class TeamCreate(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Audit Log ---

class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


# --- Transcript ---

class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class TranscriptResponse(BaseModel):
    id: int
    call_id: int
    full_text: str
    segments: Optional[list[TranscriptSegment]] = None

    model_config = {"from_attributes": True}


# --- Scores ---

class CallScoreResponse(BaseModel):
    id: int
    call_id: int
    rep_score: Optional[float] = None
    rep_tone: Optional[float] = None
    rep_steering: Optional[float] = None
    rep_service: Optional[float] = None
    rep_reasoning: Optional[str] = None
    lead_score: Optional[float] = None
    lead_service_match: Optional[float] = None
    lead_insurance: Optional[float] = None
    lead_intent: Optional[float] = None
    lead_reasoning: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Conversion Status ---

class ConversionStatusResponse(BaseModel):
    id: int
    call_id: int
    gclid: Optional[str] = None
    lead_score: Optional[float] = None
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Call ---

class CallAssignRequest(BaseModel):
    rep_id: int


class CallSummary(BaseModel):
    id: int
    call_date: Optional[datetime] = None
    duration: Optional[float] = None
    status: str
    source_type: str
    campaign_name: Optional[str] = None
    keyword: Optional[str] = None
    caller_phone: Optional[str] = None
    rep_score: Optional[float] = None
    lead_score: Optional[float] = None
    rep_name: Optional[str] = None
    conversion_status: Optional[str] = None

    model_config = {"from_attributes": True}


class CallDetail(BaseModel):
    id: int
    created_at: datetime
    ctm_call_id: Optional[str] = None
    caller_phone: Optional[str] = None
    receiving_number: Optional[str] = None
    duration: Optional[float] = None
    call_date: Optional[datetime] = None
    campaign_name: Optional[str] = None
    keyword: Optional[str] = None
    landing_page_url: Optional[str] = None
    gclid: Optional[str] = None
    audio_filename: Optional[str] = None
    status: str
    source_type: str
    error_message: Optional[str] = None
    rep_id: Optional[int] = None
    rep_name: Optional[str] = None
    transcript: Optional[TranscriptResponse] = None
    score: Optional[CallScoreResponse] = None
    conversion: Optional[ConversionStatusResponse] = None

    model_config = {"from_attributes": True}


class CallStatusResponse(BaseModel):
    id: int
    status: str
    error_message: Optional[str] = None


# --- Dashboard ---

class DashboardStats(BaseModel):
    total_calls: int
    completed_calls: int
    avg_rep_score: Optional[float] = None
    avg_lead_score: Optional[float] = None
    recent_calls: list[CallSummary]


# --- Reports ---

class TrendBucket(BaseModel):
    start_date: str
    end_date: str
    call_count: int = 0
    avg_rep_score: Optional[float] = None
    avg_lead_score: Optional[float] = None


class CampaignStats(BaseModel):
    campaign_name: str
    call_count: int = 0
    avg_lead_score: Optional[float] = None
    avg_rep_score: Optional[float] = None
    total_conversions_sent: int = 0


class RepStats(BaseModel):
    rep_id: int
    rep_name: str
    call_count: int = 0
    avg_rep_score: Optional[float] = None
```

**Step 2: Verify no import errors**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from models.schemas import *; print('OK')"
```

Expected: `OK`

---

### Task 5: Update main.py — Remove Twilio router

**Files:**
- Modify: `backend/main.py`

**Step 1: Write the new main.py**

```python
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from config import STORAGE_DIR
from routers import calls, upload, auth, users, teams, audit, reports

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="CTM Scorer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://localhost:3000", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/audio", StaticFiles(directory=str(STORAGE_DIR)), name="audio")

app.include_router(calls.router)
app.include_router(upload.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(audit.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

**Step 2: Verify app starts without errors**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from main import app; print('OK')"
```

Expected: `OK` (may fail until routers are updated — that's Task 6)

---

### Task 6: Update routers/calls.py — Remove Twilio/review references

**Files:**
- Modify: `backend/routers/calls.py`

**Step 1: Read the current calls.py to understand what needs changing**

Read the file, then update it:
- Remove any imports of `TonalityResult`, `Review`, `TwilioTokenResponse`, `DialRequest`, etc.
- Remove dial endpoint if present
- Update Call queries to use new field names (e.g., `call_date` instead of `date`, no `title`)
- Update CallSummary construction to use `rep_score`, `lead_score` from new CallScore model
- Update CallDetail construction to include `score` and `conversion` relationships
- Add PATCH `/api/calls/{id}/assign` endpoint for manual rep assignment
- Update scope filter to use `rep_id` instead of `uploaded_by`

**Step 2: Run import check**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from routers.calls import router; print('OK')"
```

Expected: `OK`

---

### Task 7: Update services/pipeline.py — Remove tonality, add placeholder scoring

**Files:**
- Modify: `backend/services/pipeline.py`

**Step 1: Write the new pipeline.py**

Key changes:
- Remove `TonalityResult` import and tonality analysis step
- Remove `Review` import
- Remove Twilio stereo diarization logic (CTM audio is typically mono)
- Replace old `CallScore` creation with new two-score placeholder (actual scoring is Phase 2)
- Keep: convert_to_wav, transcription step, error handling

```python
import logging
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from config import STORAGE_DIR
from database import Call, Transcript, CallScore
from services.transcription import transcribe_audio

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

        # Score (placeholder — real scoring added in Phase 2)
        logger.info("Scoring call %d", call_id)
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

**Step 2: Verify import**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from services.pipeline import process_call; print('OK')"
```

Expected: `OK`

---

### Task 8: Update dependencies.py — Change worker → rep

**Files:**
- Modify: `backend/dependencies.py`

**Step 1: Read the file, then update**

- Change all references to role `"worker"` to `"rep"`
- Update `get_call_scope_filter` to use `Call.rep_id` instead of `Call.uploaded_by`
- Remove any Twilio-related dependencies if present

**Step 2: Verify import**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from dependencies import *; print('OK')"
```

Expected: `OK`

---

### Task 9: Update routers/upload.py — Adjust for new Call model

**Files:**
- Modify: `backend/routers/upload.py`

**Step 1: Read the file, then update**

- Change `Call(title=..., source_type="upload", uploaded_by=...)` to `Call(source_type="manual_upload", rep_id=...)`
- Remove `title` field (no longer in model)
- Set `call_date` to current time on upload

**Step 2: Verify import**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from routers.upload import router; print('OK')"
```

Expected: `OK`

---

### Task 10: Update routers/auth.py — Default role to rep

**Files:**
- Modify: `backend/routers/auth.py`

**Step 1: Read the file, then update**

- Change default role from `"worker"` to `"rep"` in registration logic
- Change first-user auto-admin check if it references `"worker"`

**Step 2: Verify import**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from routers.auth import router; print('OK')"
```

Expected: `OK`

---

### Task 11: Update routers/reports.py — New report queries

**Files:**
- Modify: `backend/routers/reports.py`
- Modify: `backend/services/reports.py`

**Step 1: Read both files to understand current report logic**

**Step 2: Update services/reports.py**

- Remove sentiment/tonality references from trend queries
- Replace `overall_rating` with `rep_score` and `lead_score`
- Remove review-related queries (flagged, approved, unreviewed)
- Add campaign performance query
- Add rep performance query

**Step 3: Update routers/reports.py**

- Update trend endpoint to return `avg_rep_score`, `avg_lead_score`
- Replace team-comparison with campaign performance endpoint: `GET /api/reports/campaigns`
- Replace compliance with rep performance endpoint: `GET /api/reports/reps`
- Keep CSV/PDF export (updated for new fields)

**Step 4: Verify imports**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "from routers.reports import router; print('OK')"
```

Expected: `OK`

---

### Task 12: Update test fixtures — conftest.py

**Files:**
- Modify: `backend/tests/conftest.py`

**Step 1: Update conftest.py**

- Rename `worker_user` fixture to `rep_user`, change role from `"worker"` to `"rep"`
- Rename `worker_token` to `rep_token`, `worker_headers` to `rep_headers`
- Keep admin and supervisor fixtures as-is

```python
import sys
from unittest.mock import MagicMock

if "whisper" not in sys.modules:
    sys.modules["whisper"] = MagicMock()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db, User, Team
from auth import hash_password
from main import app

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def team(db):
    t = Team(name="Test Team")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture
def admin_user(db):
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("Admin123"),
        name="Admin User",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    from auth import create_access_token
    return create_access_token(admin_user.id)


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def supervisor_user(db, team):
    user = User(
        email="supervisor@test.com",
        hashed_password=hash_password("Super123"),
        name="Supervisor User",
        role="supervisor",
        team_id=team.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def supervisor_token(supervisor_user):
    from auth import create_access_token
    return create_access_token(supervisor_user.id)


@pytest.fixture
def supervisor_headers(supervisor_token):
    return {"Authorization": f"Bearer {supervisor_token}"}


@pytest.fixture
def rep_user(db, team):
    user = User(
        email="rep@test.com",
        hashed_password=hash_password("Rep12345"),
        name="Rep User",
        role="rep",
        team_id=team.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def rep_token(rep_user):
    from auth import create_access_token
    return create_access_token(rep_user.id)


@pytest.fixture
def rep_headers(rep_token):
    return {"Authorization": f"Bearer {rep_token}"}
```

**Step 2: Verify import**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -c "import tests.conftest; print('OK')"
```

Expected: `OK`

---

### Task 13: Update existing tests — Fix for new models

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_models.py`
- Modify: `backend/tests/test_pipeline.py`
- Modify: `backend/tests/test_reports.py`
- Modify: `backend/tests/test_scoping.py`
- Modify: `backend/tests/test_teams.py`
- Modify: `backend/tests/test_users.py`
- Modify: `backend/tests/test_audit.py`

**Step 1: Read each test file**

For each file, update:
- `worker_user` → `rep_user`, `worker_token` → `rep_token`, `worker_headers` → `rep_headers`
- `role="worker"` → `role="rep"`
- `uploaded_by` → `rep_id`
- `Call(title=..., ...)` → `Call(source_type=..., ...)` (remove title, add source_type)
- Remove any tests that reference `TonalityResult`, `Review`, `tonality`, `review`, Twilio, `dial`
- Update score assertions from `empathy`/`professionalism` to `rep_score`/`lead_score`
- Update report test assertions for new schema

**Step 2: Run all tests**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/ -v
```

Expected: All tests pass. Fix any failures before proceeding.

**Step 3: Commit**

```bash
git add -A
git commit -m "Phase 1: Fork Call Monitor, strip Twilio/review/tonality, update models to two-score system"
```

---

### Task 14: Update requirements.txt — Remove Twilio deps

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Read current requirements.txt**

**Step 2: Remove Twilio-related packages**

Remove: `twilio`

Keep everything else. Add: `google-ads` (for Phase 4, can add later).

**Step 3: Verify**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && pip install -r requirements.txt
```

Expected: Clean install, no twilio.

---

### Task 15: Verify everything works end-to-end

**Files:** None (verification only)

**Step 1: Run all tests**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m pytest tests/ -v
```

Expected: All tests pass.

**Step 2: Start the backend**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend && python -m uvicorn main:app --port 8002
```

Expected: Starts without errors. Hit `http://localhost:8002/api/health` → `{"status": "ok"}`

**Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "Phase 1: All tests passing after fork and trim"
```

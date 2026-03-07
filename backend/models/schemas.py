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

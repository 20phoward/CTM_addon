# CTM Scorer — Design Document

## Overview
Third-party call quality scoring app that integrates with CallTrackingMetrics (CTM). CTM handles call tracking, routing, and recording. This app pulls audio, scores it with AI (Rep Score + Lead Score), and feeds lead quality data back to Google Ads via offline conversions to optimize ad spend.

**Target industry:** Behavioral health / rehab. Inbound leads call from ad landing pages.

## Architecture

```
CTM (Call Ends)
  |
  v
POST /api/ctm/webhook --> FastAPI Backend
  |
  |--> Validate webhook (shared secret header)
  |--> Store call metadata (campaign, keyword, GCLID, rep, duration)
  |--> Download audio from CTM recording URL
  |--> Transcribe with Whisper (local)
  |--> Score with Claude AI (Rep Score + Lead Score)
  |      Input: transcript + CTM metadata
  |      Output: scores (0-10) + sub-scores + reasoning
  |--> Store results in database
  |
  |--> Send Lead Score to Google Ads (offline conversion via GCLID)
  |
  v
React Dashboard
  |--> Calls with scores + campaign attribution
  |--> Filter by campaign, keyword, score, date, rep
  |--> Campaign performance: avg lead score, volume, trends
  |--> Rep performance: avg rep score by agent
  |--> CSV/PDF export
```

## Tech Stack
- **Backend:** FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT (python-jose) + passlib/bcrypt
- **Transcription:** OpenAI Whisper (local, base model)
- **Scoring:** Claude API (Sonnet 4.6)
- **Google Ads:** google-ads-api Python client (offline conversions)
- **Frontend:** React 18 + Vite + Tailwind CSS + Recharts + Axios
- **Audio processing:** ffmpeg

## Approach
Fork Call Monitor codebase. Strip Twilio calling, sentiment timeline, review system, old scoring rubric. Keep auth, pipeline, transcription, frontend shell, audit logging, test infrastructure. Rework scoring to two-score model, add CTM webhook ingestion and Google Ads integration.

## Data Models

### Call
- `id`, `created_at`
- CTM: `ctm_call_id`, `caller_phone`, `receiving_number`, `duration`, `call_date`
- Attribution: `campaign_name`, `keyword`, `landing_page_url`, `gclid`
- Audio: `audio_filename`, `audio_url` (CTM source)
- Processing: `status` (pending/processing/completed/failed), `error_message`
- Assignment: `rep_id` (FK to User — from CTM or manual)
- Source: `source_type` (webhook/manual_upload)

### Transcript
- `call_id` (FK), `full_text`, `segments` (JSON)

### CallScore
- `call_id` (FK)
- Rep: `rep_score` (0-10), `rep_tone` (0-10), `rep_steering` (0-10), `rep_service` (0-10), `rep_reasoning`
- Lead: `lead_score` (0-10), `lead_service_match` (0-10), `lead_insurance` (0-10), `lead_intent` (0-10), `lead_reasoning`

### ConversionStatus
- `call_id` (FK), `gclid`, `lead_score`, `status` (pending/sent/failed), `error_message`, `sent_at`

### User
- Roles: `admin`, `supervisor`, `rep`
- First registered user auto-becomes admin
- Scoping: reps see own calls, supervisors see team's, admins see all

### Team, AuditLog
- Kept from Call Monitor, unchanged

## API Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /api/ctm/webhook | CTM secret | Receive call-ended webhook |
| GET | /api/calls | Auth+Scoped | List calls with scores + attribution |
| GET | /api/calls/{id} | Auth+Scoped | Call detail |
| POST | /api/calls/upload | Auth | Manual audio upload |
| DELETE | /api/calls/{id} | Supervisor+ | Delete call |
| PATCH | /api/calls/{id}/assign | Supervisor+ | Assign call to rep |
| POST | /api/conversions/send/{call_id} | Admin | Manual conversion send |
| GET | /api/conversions/status | Auth | Conversion statuses |
| GET | /api/reports/trends | Auth+Scoped | Score trends |
| GET | /api/reports/campaigns | Auth+Scoped | Campaign performance |
| GET | /api/reports/reps | Supervisor+ | Rep performance |
| GET | /api/reports/export/csv | Auth+Scoped | CSV export |
| GET | /api/reports/export/pdf | Auth+Scoped | PDF export |
| POST | /api/auth/register | Public | Register |
| POST | /api/auth/login | Public | Login |
| POST | /api/auth/refresh | Public | Refresh token |
| GET | /api/users/me | Auth | Current user |
| GET | /api/users | Admin | List users |
| PUT | /api/users/{id} | Admin | Update user |
| GET | /api/teams | Auth | List teams |
| POST | /api/teams | Admin | Create team |
| GET | /api/audit-log | Admin | Audit log |
| GET | /api/health | Public | Health check |

## CTM Webhook

CTM sends a POST when a call ends. Key fields:
- `call_id`, `caller_number`, `tracking_number`, `receiving_number`
- `duration`, `recording_url`
- `campaign_name`, `keyword`, `landing_page`, `gclid`

Auth: shared secret in custom HTTP header, validated on every request.

## Claude Scoring

Single API call per call. Input: transcript + metadata (duration, campaign, keyword, landing page).

Output (structured JSON):
```json
{
  "rep_score": 8, "rep_tone": 9, "rep_steering": 7, "rep_service": 8,
  "rep_reasoning": "Agent was warm and professional...",
  "lead_score": 7, "lead_service_match": 9, "lead_insurance": 5, "lead_intent": 7,
  "lead_reasoning": "Caller specifically asked about inpatient rehab..."
}
```

Cost: ~$0.01-0.03 per call (Sonnet 4.6).

## Google Ads Integration

After scoring, Lead Score sent as offline conversion tied to GCLID. Raw score (0-10) used as conversion value. Google Ads optimizes toward clicks producing higher scores. Requires developer token approval.

## Phases

1. **Foundation (Fork & Trim)** — Fork Call Monitor, strip Twilio/review/sentiment, update models, get tests passing
2. **CTM Integration + Scoring** — Webhook endpoint, audio download, Whisper transcription, Claude two-score pipeline
3. **Dashboard** — Call list, detail, filters, campaign + rep performance views
4. **Google Ads Integration** — Offline conversion upload, ConversionStatus tracking, dashboard status
5. **Reporting & Polish** — Trends, comparisons, CSV/PDF export, production readiness

## Auth Model
- Reps see their own calls, supervisors see team's, admins see all
- Call ownership: rep assignment pulled from CTM webhook data (receiving agent), with manual assignment fallback

## HIPAA Considerations
- Processes healthcare call recordings containing potential PHI
- Encryption at rest, audit logging, access controls built in
- AWS/Azure BAA required for production
- Password complexity enforced (8+ chars, mixed case, number)

## Open Items
- Confirm brother has Google Ads developer token or apply for one
- Verify exact CTM webhook payload format against their API docs
- Confirm CTM plan includes webhook/API access (confirmed: yes)
- Only scoring new calls going forward (no historical backfill)

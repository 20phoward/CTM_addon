# CTM Scorer - CLAUDE.md

## Project Overview
Call quality scoring add-on for CallTrackingMetrics (CTM). Behavioral health/rehab facility receives inbound calls from ad landing pages. CTM handles call tracking and recording; this app downloads audio, transcribes it, scores it with AI (Rep Score + Lead Score), and feeds lead quality data back to Google Ads as offline conversions.

**Status:** All 5 phases complete. 81 backend tests passing. Ready for deployment.

## Tech Stack
- **Backend:** Python 3 / FastAPI / SQLAlchemy / SQLite (dev) / PostgreSQL (prod) / Whisper / Anthropic Claude API
- **Auth:** python-jose (JWT) / passlib + bcrypt (passwords)
- **Google Ads:** google-ads-api (offline conversions, dry-run mode by default)
- **Frontend:** React 18 / Vite / Tailwind CSS / Recharts / Axios
- **Audio processing:** ffmpeg (convert to WAV 16kHz mono)

## Project Structure
```
ctm-scorer/
├── backend/
│   ├── main.py            # FastAPI app, CORS, routers
│   ├── config.py          # Environment config
│   ├── database.py        # SQLAlchemy models (User, Team, Call, CallScore, ConversionStatus)
│   ├── auth.py            # Password hashing, JWT utils
│   ├── dependencies.py    # FastAPI deps (auth, role guards, scoping)
│   ├── models/schemas.py  # Pydantic request/response schemas
│   ├── routers/
│   │   ├── calls.py       # Call CRUD, stats, assignment
│   │   ├── upload.py      # Manual audio upload
│   │   ├── ctm_webhook.py # CTM webhook (audio download, pipeline trigger)
│   │   ├── conversions.py # Google Ads conversion send/retry/status
│   │   ├── reports.py     # Trends, campaigns, reps, CSV/PDF export
│   │   ├── auth.py        # Register, login, refresh
│   │   ├── users.py       # User management
│   │   ├── teams.py       # Team management
│   │   └── audit.py       # Audit log
│   ├── services/
│   │   ├── pipeline.py    # Full processing: transcode → transcribe → score → convert
│   │   ├── transcription.py # Whisper transcription
│   │   ├── scoring.py     # Claude AI scoring (Rep + Lead)
│   │   ├── google_ads.py  # Google Ads conversion upload (with dry-run)
│   │   ├── reports.py     # Report query logic
│   │   └── audit.py       # Audit logging
│   ├── tests/             # 81 pytest tests
│   └── storage/audio/     # Downloaded audio files
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # Routing, navbar (CTM Scorer branding)
│   │   ├── api/client.js  # Axios wrapper with Bearer token, all API methods
│   │   ├── contexts/AuthContext.jsx
│   │   └── components/
│   │       ├── Dashboard.jsx      # Stats cards, recent calls
│   │       ├── CallList.jsx       # Sortable table with filters
│   │       ├── CallDetail.jsx     # Metadata, audio, scores, transcript
│   │       ├── ScoreDisplay.jsx   # Rep/Lead score visualization
│   │       ├── Reports.jsx        # Trends chart, campaign chart, rep table
│   │       ├── AudioUpload.jsx    # Drag-and-drop upload
│   │       ├── Login.jsx          # Auth form
│   │       ├── UserManagement.jsx # Admin user CRUD
│   │       ├── TeamManagement.jsx # Admin team CRUD
│   │       ├── AuditLog.jsx       # Audit trail viewer
│   │       ├── ProtectedRoute.jsx # Role-based route guard
│   │       └── InactivityTimer.jsx # Auto-logout after 15min
│   ├── vite.config.js     # Proxy to backend :8002
│   └── package.json
├── docs/plans/            # Design docs and implementation plans
├── ROADMAP.md             # Deployment and future work
└── .gitignore
```

## Running the App

### Backend (WSL)
```bash
source ~/workspace/ctm-scorer-venv/bin/activate
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend
uvicorn main:app --reload --port 8002
```

### Frontend (WSL, separate terminal)
```bash
cd ~/workspace/ctm-scorer-frontend
npx vite --host --port 5175
```

### Run Tests
```bash
source ~/workspace/ctm-scorer-venv/bin/activate
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend
python -m pytest tests/ -v
```

### First-time setup
```bash
# Python venv (must be on Linux filesystem)
python3 -m venv ~/workspace/ctm-scorer-venv
source ~/workspace/ctm-scorer-venv/bin/activate
pip install setuptools==75.8.2 wheel
pip install -r /mnt/c/Users/ticta/workspace1/ctm-scorer/backend/requirements.txt

# Frontend (must be on Linux filesystem)
cp -r /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend ~/workspace/ctm-scorer-frontend
cd ~/workspace/ctm-scorer-frontend && npm install

# Backend .env
echo "ANTHROPIC_API_KEY=your-key-here" > backend/.env
python3 -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')" >> backend/.env
echo "CTM_WEBHOOK_SECRET=your-ctm-secret" >> backend/.env
echo "GOOGLE_ADS_DRY_RUN=true" >> backend/.env
```

### System deps: `sudo apt install ffmpeg nodejs npm python3.12-venv`

## Key Conventions
- **API prefix:** All endpoints under `/api/`
- **Auth:** JWT tokens (access 15min + refresh 7 days), Bearer header
- **Roles:** rep, supervisor, admin — first registered user auto-becomes admin
- **Data scoping:** reps see own calls, supervisors see team's, admins see all
- **Call assignment:** Pulled from CTM webhook (receiving agent), manual fallback via PATCH
- **Processing is async:** Webhook returns immediately; pipeline runs in background task
- **Status flow:** pending → processing → completed | failed
- **Two AI scores per call:** Rep Score (0-10) and Lead Score (0-10), each with sub-scores and reasoning
- **Google Ads:** Lead Score sent as offline conversion value tied to GCLID (dry-run by default)
- **HIPAA:** password complexity (8+ chars, mixed case, number), audit logging, encryption at rest

## Environment Variables
```
ANTHROPIC_API_KEY=<required for AI scoring>
SECRET_KEY=<required for JWT signing>
WHISPER_MODEL=base
DATABASE_URL=sqlite:///./calls.db
UPLOAD_DIR=./storage/audio
CTM_WEBHOOK_SECRET=<shared secret for webhook validation>

# Google Ads (required for live conversion upload)
GOOGLE_ADS_DRY_RUN=true          # Set to false for live mode
GOOGLE_ADS_DEVELOPER_TOKEN=<from Google Ads API>
GOOGLE_ADS_CLIENT_ID=<OAuth client ID>
GOOGLE_ADS_CLIENT_SECRET=<OAuth client secret>
GOOGLE_ADS_REFRESH_TOKEN=<OAuth refresh token>
GOOGLE_ADS_CUSTOMER_ID=<Google Ads account ID>
GOOGLE_ADS_CONVERSION_ACTION=<conversion action ID>
```

## Dependencies to Note
- **ffmpeg** must be installed for audio conversion
- **Whisper** downloads model on first run (~140MB for base)
- **bcrypt** pinned to 4.0.1 (passlib incompatible with 5.x)
- **setuptools** pinned to 75.8.2 (Whisper needs pkg_resources)
- **google-ads** package only needed when `GOOGLE_ADS_DRY_RUN=false` (commented in requirements.txt)
- Frontend proxies `/api` and `/audio` to backend :8002 in dev

## When Making Changes
- Backend schemas in `models/schemas.py` — update when adding DB fields
- New API routes in `routers/`, register in `main.py`
- Auth deps in `dependencies.py` — use `get_current_user`, `require_admin`, `require_supervisor_or_admin`, `get_call_scope_filter`
- Audit logging via `services/audit.py`
- Services in `services/` — keep business logic out of routers
- Frontend API calls through `api/client.js`
- Tailwind for styling
- After schema changes, delete `calls.db` to recreate (no migrations yet)

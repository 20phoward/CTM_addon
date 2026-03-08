# Render Deployment Design

## Goal
Deploy CTM Scorer (backend + frontend + database) to Render free tier for demo/testing.

## Architecture
- **Backend:** Render Web Service (Python, free tier) — FastAPI + uvicorn
- **Frontend:** Render Static Site (free tier) — Vite production build
- **Database:** Render PostgreSQL (free tier, 90-day limit)
- **Audio storage:** Local filesystem (ephemeral, acceptable for demo)

## Constraints
- Free tier spins down after 15min idle (~30sec cold start)
- PostgreSQL free tier expires after 90 days
- Audio files lost on redeploy (no persistent storage on free tier)
- Good enough for demo/testing; upgrade to paid (~$7/month) for production

## Changes Required

### 1. render.yaml (Blueprint)
Infrastructure-as-code file at project root. Defines:
- Web service for backend (Python 3, port 8002)
- Static site for frontend (Vite build)
- PostgreSQL database
- Environment variable references

### 2. backend/render_start.sh
Startup script:
- Install dependencies from requirements.txt
- Start uvicorn on 0.0.0.0:$PORT

### 3. backend/config.py
- Fix DATABASE_URL scheme: Render provides `postgres://` but SQLAlchemy requires `postgresql://`
- Ensure all config reads from environment variables (already mostly done)

### 4. Frontend production build
- Update vite.config.js: set API base URL via env var for production (no dev proxy in prod)
- Update api/client.js: use full backend URL when not in dev mode
- Build command: `npm install && npm run build`
- Publish directory: `dist`

### 5. CORS
- Backend CORS must allow the frontend's Render URL (e.g., `https://ctm-scorer-frontend.onrender.com`)

## Deploy Flow
1. Push changes to GitHub
2. Create Render account, connect GitHub repo
3. Use render.yaml blueprint to create all services
4. Set environment variables in Render dashboard:
   - `ANTHROPIC_API_KEY`
   - `SECRET_KEY`
   - `CTM_WEBHOOK_SECRET`
   - `DATABASE_URL` (auto-set by Render PostgreSQL)
   - `GOOGLE_ADS_DRY_RUN=true`
5. Render auto-builds and deploys

## Not Needed
- Docker (Render builds Python natively)
- Nginx (Render handles routing)
- CI/CD pipelines (Render auto-deploys from GitHub)
- Alembic migrations (fresh DB for demo, tables auto-created by SQLAlchemy)

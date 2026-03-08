# Railway Deployment Design

## Goal
Deploy CTM Scorer (backend + frontend + database) to Railway for demo/testing.

## Architecture
- **Backend:** Railway Web Service (Python) — FastAPI + uvicorn
- **Frontend:** Railway Web Service (Node) — Vite build served with `serve`
- **Database:** Railway PostgreSQL plugin
- **Audio storage:** Local filesystem (ephemeral, acceptable for demo)

## Constraints
- $5 free credit/month (enough for light demo/testing)
- Audio files lost on redeploy (no persistent volume on free tier)
- Good enough for demo/testing; upgrade for production

## Changes Made

### 1. backend/config.py
- Fixed DATABASE_URL scheme: Railway uses `postgres://` but SQLAlchemy requires `postgresql://`
- Added `CORS_ORIGINS` env var for configurable CORS

### 2. backend/database.py
- Made `check_same_thread` connect arg conditional on SQLite (PostgreSQL doesn't support it)

### 3. backend/requirements.txt
- Added `psycopg2-binary==2.9.9` for PostgreSQL driver

### 4. frontend/src/api/client.js
- `VITE_API_URL` env var for production API base URL
- `audioUrl()` derives base from same env var

### 5. backend/railway.json
- Railpack builder, uvicorn start command, health check at `/api/health`

### 6. frontend/railway.json
- Railpack builder, `serve` for static file serving with SPA rewrite

### 7. CORS
- Backend CORS reads from `CORS_ORIGINS` env var

## Deploy Flow
1. Push changes to GitHub
2. Create Railway account, new project
3. Add PostgreSQL plugin → copies `DATABASE_URL` to backend service
4. Add backend service → connect GitHub repo, set root directory to `backend/`
5. Add frontend service → connect GitHub repo, set root directory to `frontend/`
6. Set env vars on backend: `ANTHROPIC_API_KEY`, `SECRET_KEY`, `CTM_WEBHOOK_SECRET`, `CORS_ORIGINS`, `GOOGLE_ADS_DRY_RUN=true`
7. Set env var on frontend: `VITE_API_URL=https://<backend-url>/api`
8. Deploy

## Not Needed
- Docker (Railway auto-detects Python/Node)
- Nginx (Railway handles routing)
- CI/CD pipelines (Railway auto-deploys from GitHub)
- Alembic migrations (fresh DB for demo, tables auto-created by SQLAlchemy)

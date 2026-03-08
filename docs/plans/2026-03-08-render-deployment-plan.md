# Render Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy CTM Scorer backend + frontend + PostgreSQL to Render free tier.

**Architecture:** Render Web Service for FastAPI backend, Render Static Site for Vite-built frontend, Render PostgreSQL for database. All defined in a `render.yaml` blueprint for one-click setup.

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy / PostgreSQL / React 18 / Vite / Render

---

### Task 1: Fix DATABASE_URL for PostgreSQL compatibility

**Files:**
- Modify: `backend/config.py:11`
- Modify: `backend/database.py:10`

**Step 1: Update config.py to fix postgres:// scheme**

Render provides `postgres://` but SQLAlchemy 2.x requires `postgresql://`. Add scheme replacement.

Edit `backend/config.py:11` — replace the DATABASE_URL line:

```python
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'calls.db'}")
# Render uses postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
```

**Step 2: Remove SQLite-only connect_args from database.py**

Edit `backend/database.py:10` — the `check_same_thread` arg only works with SQLite. Make it conditional:

```python
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
```

**Step 3: Add psycopg2-binary to requirements.txt**

PostgreSQL needs a driver. Add to `backend/requirements.txt`:

```
psycopg2-binary==2.9.9
```

**Step 4: Run existing tests to make sure nothing broke**

Run:
```bash
source ~/workspace/ctm-scorer-venv/bin/activate
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend
python -m pytest tests/ -v
```
Expected: All 81 tests PASS (they use SQLite, so this change should be transparent)

**Step 5: Commit**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer
git add backend/config.py backend/database.py backend/requirements.txt
git commit -m "feat: add PostgreSQL support for Render deployment"
```

---

### Task 2: Make CORS configurable for production

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/main.py:15-21`

**Step 1: Add CORS_ORIGINS to config.py**

Add at the end of `backend/config.py`:

```python
# CORS — comma-separated origins, or "*" for dev
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5175,http://localhost:3000,http://127.0.0.1:5175")
```

**Step 2: Update main.py to use config**

Edit `backend/main.py` — replace the hardcoded origins:

```python
from config import STORAGE_DIR, CORS_ORIGINS

# ... in the middleware setup:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Step 3: Run tests**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend
python -m pytest tests/ -v
```
Expected: All 81 tests PASS

**Step 4: Commit**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer
git add backend/config.py backend/main.py
git commit -m "feat: make CORS origins configurable via env var"
```

---

### Task 3: Configure frontend for production API URL

**Files:**
- Modify: `frontend/src/api/client.js:3`
- Modify: `frontend/vite.config.js`

**Step 1: Update client.js to use env var for base URL**

Edit `frontend/src/api/client.js:3` — replace the hardcoded baseURL:

```javascript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api'
})
```

In dev mode (Vite proxy), `VITE_API_URL` is unset so it uses `/api` (proxied to backend).
In production, set `VITE_API_URL` to the full backend URL like `https://ctm-scorer-api.onrender.com/api`.

**Step 2: Update audioUrl function**

Edit `frontend/src/api/client.js` — update the audioUrl function:

```javascript
export function audioUrl(filename) {
  const base = import.meta.env.VITE_API_URL?.replace('/api', '') || ''
  return `${base}/audio/${filename}`
}
```

**Step 3: Commit**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer
git add frontend/src/api/client.js
git commit -m "feat: make API base URL configurable for production"
```

---

### Task 4: Create render.yaml blueprint

**Files:**
- Create: `render.yaml`

**Step 1: Create render.yaml at project root**

```yaml
databases:
  - name: ctm-scorer-db
    plan: free
    databaseName: ctm_scorer
    user: ctm_scorer

services:
  - type: web
    name: ctm-scorer-api
    runtime: python
    plan: free
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: ctm-scorer-db
          property: connectionString
      - key: SECRET_KEY
        generateValue: true
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: CTM_WEBHOOK_SECRET
        sync: false
      - key: GOOGLE_ADS_DRY_RUN
        value: "true"
      - key: WHISPER_MODEL
        value: base
      - key: PYTHON_VERSION
        value: "3.12.0"
      - key: CORS_ORIGINS
        value: "https://ctm-scorer-frontend.onrender.com"

  - type: web
    name: ctm-scorer-frontend
    runtime: static
    plan: free
    rootDir: frontend
    buildCommand: npm install && npm run build
    staticPublishPath: dist
    envVars:
      - key: VITE_API_URL
        value: "https://ctm-scorer-api.onrender.com/api"
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
```

**Step 2: Commit**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer
git add render.yaml
git commit -m "feat: add render.yaml blueprint for one-click deployment"
```

---

### Task 5: Add health check and fix package.json name

**Files:**
- Modify: `frontend/package.json:2`

**Step 1: Fix package.json name**

Edit `frontend/package.json` — change name from `call-monitor-frontend` to `ctm-scorer-frontend`:

```json
"name": "ctm-scorer-frontend",
```

**Step 2: Verify backend health endpoint exists**

The health endpoint already exists at `/api/health` in `backend/main.py:41-43`. No changes needed. Render will use this for health checks.

**Step 3: Commit**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer
git add frontend/package.json
git commit -m "fix: rename package.json from call-monitor to ctm-scorer"
```

---

### Task 6: Final verification and push

**Step 1: Run all backend tests**

```bash
source ~/workspace/ctm-scorer-venv/bin/activate
cd /mnt/c/Users/ticta/workspace1/ctm-scorer/backend
python -m pytest tests/ -v
```
Expected: All 81 tests PASS

**Step 2: Test frontend build**

```bash
cd ~/workspace/ctm-scorer-frontend
# Copy updated frontend files from Windows
cp -r /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend/src ~/workspace/ctm-scorer-frontend/src
cp /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend/vite.config.js ~/workspace/ctm-scorer-frontend/
cp /mnt/c/Users/ticta/workspace1/ctm-scorer/frontend/package.json ~/workspace/ctm-scorer-frontend/
npm run build
```
Expected: Build succeeds, output in `dist/`

**Step 3: Push to GitHub**

```bash
cd /mnt/c/Users/ticta/workspace1/ctm-scorer
git push origin main
```

**Step 4: Deploy on Render**

1. Go to https://render.com — sign up / log in
2. Click "New" → "Blueprint"
3. Connect your GitHub repo (`20phoward/CTM_addon`)
4. Render reads `render.yaml` and creates all 3 services
5. Set the `ANTHROPIC_API_KEY` and `CTM_WEBHOOK_SECRET` env vars in the Render dashboard
6. Wait for builds to complete (~5-10 min)
7. Visit `https://ctm-scorer-frontend.onrender.com` to verify

**Note:** After Render assigns actual URLs (which may differ from the names in render.yaml), update:
- `CORS_ORIGINS` env var on the backend service to match the actual frontend URL
- `VITE_API_URL` env var on the frontend service to match the actual backend URL
- Trigger a rebuild of the frontend after changing `VITE_API_URL`

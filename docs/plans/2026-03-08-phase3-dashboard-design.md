# Phase 3: Dashboard Design

**Goal:** Update the React frontend from Call Monitor's old sentiment/review UI to a CTM call scoring dashboard showing Rep Scores, Lead Scores, campaign attribution, and rep performance.

**Architecture:** Update existing React components to consume the already-built backend API. No new libraries needed — Recharts + Tailwind handle everything. Remove dead Twilio/sentiment/review code.

**Tech Stack:** React 18, Vite, Tailwind CSS, Recharts, Axios

---

## Pages

### 1. Dashboard (home page)
- 4 stat cards: Total Calls, Completed Calls, Avg Rep Score, Avg Lead Score
- Recent calls table (top 5) with scores and status
- Remove old sentiment/review/flagged stats

### 2. Call List
- Columns: Date, Caller, Campaign, Duration, Rep Score, Lead Score, Rep, Status
- Color-coded scores (green 8+, yellow 6-7, orange 4-5, red <4)
- Filters: status, campaign, date range
- Sort by any column
- Remove old sentiment/review columns

### 3. Call Detail
- Call metadata: date, caller phone, campaign, keyword, landing page, GCLID, rep
- Audio player
- Score cards: Rep Score breakdown (tone, steering, service + reasoning) and Lead Score breakdown (service match, insurance, intent + reasoning)
- Transcript with segments
- New ScoreDisplay component replaces old TonalityChart/ScoreCard/ReviewPanel
- Conversion status badge (if GCLID present)

### 4. Reports (update existing)
- Trends: line chart of avg rep/lead scores over time
- Campaigns: bar chart of campaign performance (call count, avg lead score)
- Reps: table of rep performance (call count, avg rep score) — supervisor/admin only
- CSV/PDF export (already wired in backend)
- Remove old team comparison and compliance sections

### 5. Cleanup
- Remove CallDialer route and import
- Update API client: remove Twilio/review methods, add campaigns/reps endpoints
- Fix vite proxy port (8000 → 8002)
- Update role badge: "worker" → "rep"

## Backend API (already built)

- `GET /api/calls` → CallSummary list
- `GET /api/calls/{id}` → CallDetail with score, transcript, conversion
- `GET /api/calls/stats` → DashboardStats (total, completed, avg scores, recent)
- `GET /api/calls/{id}/scores` → CallScoreResponse (all sub-scores + reasoning)
- `GET /api/reports/trends` → TrendBucket list
- `GET /api/reports/campaigns` → CampaignStats list
- `GET /api/reports/reps` → RepStats list
- `GET /api/reports/export/csv` → CSV download
- `GET /api/reports/export/pdf` → PDF download

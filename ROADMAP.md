# CTM Scorer — Roadmap

## Completed

### Phase 1: Fork & Trim
- Forked from Call Monitor, stripped Twilio/sentiment/review system
- Adapted auth, models, and tests for CTM scoring use case
- 55 tests passing

### Phase 2: CTM Integration + Scoring
- CTM webhook endpoint with shared secret validation
- Audio download, ffmpeg transcode, Whisper transcription
- Claude AI dual scoring (Rep Score + Lead Score, 0-10 each)
- Background processing pipeline
- 67 tests passing

### Phase 3: Dashboard Frontend
- Updated all React components for CTM scoring (removed Call Monitor UI)
- Dashboard with stats cards, call list with filters/sorting
- ScoreDisplay component with color-coded rings and sub-score bars
- CallDetail with metadata grid, audio player, transcript viewer
- Reports with score trends, campaign performance, rep performance table
- Rebranded "Call Monitor" → "CTM Scorer", "worker" → "rep"

### Phase 4: Google Ads Integration
- Offline conversion upload via GCLID
- Dry-run mode (default) for safe testing without live credentials
- ConversionStatus model tracking send attempts
- Admin retry/send UI on CallDetail page
- Conversions status list endpoint
- 81 tests passing

### Phase 5: Reporting & Polish
- Fixed trends data format bug (buckets extraction)
- Conversion status UI on CallDetail
- Code cleanup and final polish
- 81 tests passing

## Deployment Checklist

1. **Server setup** — Deploy backend (FastAPI + uvicorn) and frontend (Vite build → static hosting)
2. **Database** — Switch from SQLite to PostgreSQL (`DATABASE_URL` env var)
3. **CTM webhook** — Configure CTM to POST to `/api/ctm/webhook` with `X-CTM-Secret` header
4. **Environment variables** — Set `ANTHROPIC_API_KEY`, `SECRET_KEY`, `CTM_WEBHOOK_SECRET`
5. **Google Ads** (when ready):
   - `pip install google-ads>=24.0.0`
   - Set `GOOGLE_ADS_DRY_RUN=false`
   - Configure OAuth credentials (`CLIENT_ID`, `CLIENT_SECRET`, `REFRESH_TOKEN`)
   - Set `GOOGLE_ADS_CUSTOMER_ID` and `GOOGLE_ADS_CONVERSION_ACTION`

## Future Work

- **Database migrations** — Add Alembic for schema changes without data loss
- **Bulk operations** — Batch re-score, bulk delete, bulk conversion send
- **Notification system** — Email/Slack alerts for low rep scores or high-value leads
- **Call recording playback** — Stream audio from CTM instead of downloading
- **Multi-facility support** — Separate data per facility/location
- **Advanced analytics** — Score distribution histograms, time-of-day patterns
- **HIPAA hardening** — Encryption at rest, access logging, data retention policies

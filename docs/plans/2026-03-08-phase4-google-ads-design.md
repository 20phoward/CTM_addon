# Phase 4: Google Ads Offline Conversion Upload — Design

**Goal:** After scoring a call, automatically send Lead Score as an offline conversion value to Google Ads via GCLID. Includes mock/dry-run mode for testing without a live token.

## Flow

1. Pipeline scores call → if GCLID present and lead_score exists → create ConversionStatus (pending)
2. Google Ads service uploads conversion (or logs in mock mode)
3. ConversionStatus updated to `sent` / `sent (dry_run)` / `failed`
4. Admin can manually trigger/retry via API

## Mock Mode

When `GOOGLE_ADS_DRY_RUN=true` or `GOOGLE_ADS_CUSTOMER_ID` is empty, the service logs the conversion payload and marks status as `sent (dry_run)`. No actual API call made.

## Endpoints

- `POST /api/conversions/send/{call_id}` — Admin triggers conversion upload (or retry)
- `GET /api/conversions/status` — List all conversion statuses with optional filters

## Auto-Send

Pipeline automatically calls conversion service after scoring if GCLID present. No cron needed — runs in the same background task.

## Google Ads API

- Package: `google-ads` Python client
- Conversion action name from env var: `GOOGLE_ADS_CONVERSION_ACTION`
- Customer ID from env var: `GOOGLE_ADS_CUSTOMER_ID`
- Auth: OAuth2 refresh token flow (client_id, client_secret, refresh_token, developer_token from env)

## Existing Infrastructure

- `ConversionStatus` model already exists in `database.py`
- `ConversionStatusResponse` schema exists in `models/schemas.py`
- GCLID captured from CTM webhook payload
- Call detail page already shows conversion status badge

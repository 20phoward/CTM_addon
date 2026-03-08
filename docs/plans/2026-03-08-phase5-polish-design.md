# Phase 5: Polish & Cleanup — Design

**Goal:** Fix remaining bugs, wire up conversion endpoints in frontend, clean up dead files.

## Tasks

1. **Fix Reports trends data format** — Backend returns `{period, buckets: [...]}`, frontend expects flat array. Align them.
2. **Add conversion endpoints to frontend** — Wire `/api/conversions/send/{id}` and `/api/conversions/status` into API client. Add retry button on CallDetail when conversion failed.
3. **Delete dead files** — Remove CallDialer.jsx and any other Call Monitor leftovers.
4. **Final test run and push**

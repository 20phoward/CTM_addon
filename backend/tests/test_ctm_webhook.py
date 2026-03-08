from unittest.mock import patch
from database import Call


def test_webhook_missing_secret(client):
    resp = client.post("/api/ctm/webhook", json={"id": "123"})
    assert resp.status_code == 403


def test_webhook_invalid_secret(client):
    resp = client.post("/api/ctm/webhook", json={"id": "123"},
                       headers={"X-CTM-Secret": "wrong-secret"})
    assert resp.status_code == 403


def test_webhook_creates_call(client, db):
    payload = {
        "id": "ctm-call-456",
        "caller_number": "+15551234567",
        "tracking_number": "+15559876543",
        "receiving_number": "+15551112222",
        "duration": 180,
        "recording_url": "https://ctm.example.com/recordings/456.mp3",
        "campaign_name": "Rehab Campaign",
        "keyword": "inpatient rehab",
        "landing_page": "https://example.com/rehab",
        "gclid": "test-gclid-abc123",
    }

    with patch("routers.ctm_webhook.CTM_WEBHOOK_SECRET", "test-secret"), \
         patch("routers.ctm_webhook.download_ctm_audio", return_value="ctm-call-456.mp3"):
        resp = client.post("/api/ctm/webhook", json=payload,
                           headers={"X-CTM-Secret": "test-secret"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["ctm_call_id"] == "ctm-call-456"
    assert data["status"] == "pending"

    call = db.query(Call).filter(Call.ctm_call_id == "ctm-call-456").first()
    assert call is not None
    assert call.campaign_name == "Rehab Campaign"
    assert call.gclid == "test-gclid-abc123"
    assert call.caller_phone == "+15551234567"


def test_webhook_duplicate_call_id(client, db):
    existing = Call(ctm_call_id="ctm-dup-789", status="completed")
    db.add(existing)
    db.commit()

    payload = {"id": "ctm-dup-789", "recording_url": "https://example.com/rec.mp3"}

    with patch("routers.ctm_webhook.CTM_WEBHOOK_SECRET", "test-secret"):
        resp = client.post("/api/ctm/webhook", json=payload,
                           headers={"X-CTM-Secret": "test-secret"})

    assert resp.status_code == 409


def test_webhook_no_recording_url(client, db):
    payload = {"id": "ctm-no-rec-999"}

    with patch("routers.ctm_webhook.CTM_WEBHOOK_SECRET", "test-secret"):
        resp = client.post("/api/ctm/webhook", json=payload,
                           headers={"X-CTM-Secret": "test-secret"})

    assert resp.status_code == 400

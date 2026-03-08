from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal, Call, CallScore, ConversionStatus


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    client.post("/api/auth/register", json={
        "email": "convadmin@test.com", "password": "Admin123!", "name": "Conv Admin"
    })
    resp = client.post("/api/auth/login", json={
        "email": "convadmin@test.com", "password": "Admin123!"
    })
    return resp.json()["access_token"]


@pytest.fixture
def rep_token(client, admin_token):
    client.post("/api/auth/register", json={
        "email": "convrep@test.com", "password": "Rep12345!", "name": "Conv Rep"
    })
    resp = client.post("/api/auth/login", json={
        "email": "convrep@test.com", "password": "Rep12345!"
    })
    return resp.json()["access_token"]


@pytest.fixture
def scored_call_with_gclid():
    db = SessionLocal()
    try:
        call = Call(
            source_type="ctm_webhook",
            audio_filename="test.wav",
            status="completed",
            gclid="test-gclid-conv",
            call_date=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        score = CallScore(call_id=call.id, lead_score=8.0, rep_score=7.0)
        db.add(score)
        db.commit()

        return call.id
    finally:
        db.close()


def test_send_conversion_creates_status(client, admin_token, scored_call_with_gclid):
    with patch("routers.conversions.upload_conversion", return_value={
        "status": "sent (dry_run)", "gclid": "test-gclid-conv",
        "conversion_value": 8.0, "error": None,
    }):
        resp = client.post(
            f"/api/conversions/send/{scored_call_with_gclid}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent (dry_run)"
    assert data["gclid"] == "test-gclid-conv"


def test_send_conversion_requires_admin(client, rep_token, scored_call_with_gclid):
    resp = client.post(
        f"/api/conversions/send/{scored_call_with_gclid}",
        headers={"Authorization": f"Bearer {rep_token}"},
    )
    assert resp.status_code == 403


def test_send_conversion_404_for_missing_call(client, admin_token):
    resp = client.post(
        "/api/conversions/send/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_send_conversion_400_no_gclid(client, admin_token):
    db = SessionLocal()
    try:
        call = Call(source_type="manual_upload", audio_filename="x.wav", status="completed")
        db.add(call)
        db.commit()
        db.refresh(call)
        call_id = call.id
    finally:
        db.close()

    resp = client.post(
        f"/api/conversions/send/{call_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "gclid" in resp.json()["detail"].lower()


def test_list_conversions(client, admin_token, scored_call_with_gclid):
    db = SessionLocal()
    try:
        conv = ConversionStatus(
            call_id=scored_call_with_gclid,
            gclid="test-gclid-conv",
            lead_score=8.0,
            status="sent (dry_run)",
        )
        db.add(conv)
        db.commit()
    finally:
        db.close()

    resp = client.get(
        "/api/conversions/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["gclid"] == "test-gclid-conv"


def test_list_conversions_filter_by_status(client, admin_token, scored_call_with_gclid):
    db = SessionLocal()
    try:
        conv = ConversionStatus(
            call_id=scored_call_with_gclid,
            gclid="test-gclid-conv",
            lead_score=8.0,
            status="failed",
            error_message="test error",
        )
        db.add(conv)
        db.commit()
    finally:
        db.close()

    resp = client.get(
        "/api/conversions/status?status=failed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(c["status"] == "failed" for c in data)

"""Tests for the reports service and endpoints."""
from datetime import datetime, timezone, timedelta
from database import Call, CallScore


def _make_call(db, user, days_ago=0, rep_score=8.0, lead_score=7.0, campaign=None, keyword=None):
    """Helper to create a completed call with scores."""
    call = Call(
        status="completed",
        rep_id=user.id,
        call_date=datetime.now(timezone.utc) - timedelta(days=days_ago),
        campaign_name=campaign,
        keyword=keyword,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    score = CallScore(call_id=call.id, rep_score=rep_score, lead_score=lead_score)
    db.add(score)
    db.commit()
    return call


# --- Trends ---

def test_trends_returns_buckets(client, admin_headers, admin_user, db):
    _make_call(db, admin_user, days_ago=5, rep_score=8.0, lead_score=7.0)
    _make_call(db, admin_user, days_ago=3, rep_score=6.0, lead_score=5.0)

    resp = client.get("/api/reports/trends?period=weekly", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "weekly"
    assert len(data["buckets"]) >= 1
    total = sum(b["call_count"] for b in data["buckets"])
    assert total == 2


def test_trends_date_filter(client, admin_headers, admin_user, db):
    _make_call(db, admin_user, days_ago=100)
    _make_call(db, admin_user, days_ago=5)

    start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resp = client.get(f"/api/reports/trends?start_date={start}&end_date={end}", headers=admin_headers)
    assert resp.status_code == 200
    total = sum(b["call_count"] for b in resp.json()["buckets"])
    assert total == 1


def test_trends_rep_scoping(client, rep_headers, rep_user, admin_user, db):
    _make_call(db, rep_user, days_ago=3)
    _make_call(db, admin_user, days_ago=3)

    resp = client.get("/api/reports/trends", headers=rep_headers)
    assert resp.status_code == 200
    total = sum(b["call_count"] for b in resp.json()["buckets"])
    assert total == 1


# --- Campaigns ---

def test_campaigns_report(client, admin_headers, admin_user, db):
    _make_call(db, admin_user, days_ago=3, lead_score=8.0, campaign="Rehab Campaign")
    _make_call(db, admin_user, days_ago=2, lead_score=6.0, campaign="Rehab Campaign")
    _make_call(db, admin_user, days_ago=1, lead_score=9.0, campaign="Detox Campaign")

    resp = client.get("/api/reports/campaigns", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    rehab = next(c for c in data if c["campaign_name"] == "Rehab Campaign")
    assert rehab["call_count"] == 2
    assert rehab["avg_lead_score"] == 7.0


# --- Reps ---

def test_reps_report(client, admin_headers, admin_user, rep_user, db):
    _make_call(db, admin_user, days_ago=3, rep_score=9.0)
    _make_call(db, rep_user, days_ago=3, rep_score=7.0)

    resp = client.get("/api/reports/reps", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_reps_report_rep_denied(client, rep_headers):
    resp = client.get("/api/reports/reps", headers=rep_headers)
    assert resp.status_code == 403


# --- Export ---

def test_export_csv(client, admin_headers, admin_user, db):
    _make_call(db, admin_user, days_ago=3)

    resp = client.get("/api/reports/export/csv", headers=admin_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")
    lines = resp.text.strip().split("\n")
    assert len(lines) == 2  # header + 1 data row


def test_export_pdf(client, admin_headers, admin_user, db):
    _make_call(db, admin_user, days_ago=3)

    resp = client.get("/api/reports/export/pdf", headers=admin_headers)
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]
    assert resp.content[:5] == b"%PDF-"


def test_no_auth_returns_403(client):
    resp = client.get("/api/reports/trends")
    assert resp.status_code == 403

from database import Call, CallScore


def test_get_scores(client, admin_headers, admin_user, db):
    call = Call(status="completed", rep_id=admin_user.id)
    db.add(call)
    db.commit()
    score = CallScore(
        call_id=call.id, rep_score=8.0, rep_tone=9.0,
        rep_steering=7.0, rep_service=8.0, rep_reasoning="Good call handling",
        lead_score=7.0, lead_service_match=8.0,
        lead_insurance=5.0, lead_intent=8.0, lead_reasoning="Strong intent",
    )
    db.add(score)
    db.commit()

    resp = client.get(f"/api/calls/{call.id}/scores", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["rep_score"] == 8.0
    assert data["lead_score"] == 7.0
    assert data["rep_reasoning"] == "Good call handling"


def test_get_scores_not_found(client, admin_headers, admin_user, db):
    call = Call(status="completed", rep_id=admin_user.id)
    db.add(call)
    db.commit()

    resp = client.get(f"/api/calls/{call.id}/scores", headers=admin_headers)
    assert resp.status_code == 404


def test_list_calls_includes_scores(client, admin_headers, admin_user, db):
    call = Call(status="completed", rep_id=admin_user.id)
    db.add(call)
    db.commit()
    db.add(CallScore(call_id=call.id, rep_score=8.0, lead_score=7.0))
    db.commit()

    resp = client.get("/api/calls", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["rep_score"] == 8.0
    assert data[0]["lead_score"] == 7.0


def test_dashboard_stats(client, admin_headers, admin_user, db):
    for i in range(3):
        call = Call(status="completed", rep_id=admin_user.id)
        db.add(call)
        db.commit()
        db.add(CallScore(call_id=call.id, rep_score=8.0, lead_score=6.0))
        db.commit()

    resp = client.get("/api/calls/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 3
    assert data["completed_calls"] == 3
    assert data["avg_rep_score"] == 8.0
    assert data["avg_lead_score"] == 6.0


def test_assign_call(client, admin_headers, admin_user, rep_user, db):
    call = Call(status="completed")
    db.add(call)
    db.commit()

    resp = client.patch(f"/api/calls/{call.id}/assign",
                        json={"rep_id": rep_user.id}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["rep_id"] == rep_user.id


def test_assign_call_rep_not_found(client, admin_headers, db):
    call = Call(status="completed")
    db.add(call)
    db.commit()

    resp = client.patch(f"/api/calls/{call.id}/assign",
                        json={"rep_id": 9999}, headers=admin_headers)
    assert resp.status_code == 404

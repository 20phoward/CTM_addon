from database import Call


def test_rep_sees_only_own_calls(client, rep_headers, rep_user, admin_user, db):
    call1 = Call(rep_id=rep_user.id, status="completed")
    call2 = Call(rep_id=admin_user.id, status="completed")
    db.add_all([call1, call2])
    db.commit()

    response = client.get("/api/calls", headers=rep_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_supervisor_sees_team_calls(client, supervisor_headers, supervisor_user, rep_user, admin_user, db):
    call1 = Call(rep_id=rep_user.id, status="completed")
    call2 = Call(rep_id=admin_user.id, status="completed")
    db.add_all([call1, call2])
    db.commit()

    response = client.get("/api/calls", headers=supervisor_headers)
    assert response.status_code == 200
    # Supervisor sees team member (rep_user) calls + unassigned, not admin's
    ids = [c["id"] for c in response.json()]
    assert call1.id in ids
    assert call2.id not in ids


def test_admin_sees_all_calls(client, admin_headers, rep_user, admin_user, db):
    call1 = Call(rep_id=rep_user.id, status="completed")
    call2 = Call(rep_id=admin_user.id, status="completed")
    db.add_all([call1, call2])
    db.commit()

    response = client.get("/api/calls", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_rep_cannot_view_others_call(client, rep_headers, admin_user, db):
    call = Call(rep_id=admin_user.id, status="completed")
    db.add(call)
    db.commit()
    db.refresh(call)

    response = client.get(f"/api/calls/{call.id}", headers=rep_headers)
    assert response.status_code == 403


def test_rep_cannot_delete(client, rep_headers, rep_user, db):
    call = Call(rep_id=rep_user.id, status="completed")
    db.add(call)
    db.commit()
    db.refresh(call)

    response = client.delete(f"/api/calls/{call.id}", headers=rep_headers)
    assert response.status_code == 403


def test_supervisor_can_delete_team_call(client, supervisor_headers, rep_user, db):
    call = Call(rep_id=rep_user.id, status="completed")
    db.add(call)
    db.commit()
    db.refresh(call)

    response = client.delete(f"/api/calls/{call.id}", headers=supervisor_headers)
    assert response.status_code == 200


def test_no_auth_returns_403(client, db):
    call = Call(status="completed")
    db.add(call)
    db.commit()

    response = client.get("/api/calls")
    assert response.status_code == 403


def test_stats_scoped_to_rep(client, rep_headers, rep_user, admin_user, db):
    call1 = Call(rep_id=rep_user.id, status="completed")
    call2 = Call(rep_id=admin_user.id, status="completed")
    db.add_all([call1, call2])
    db.commit()

    response = client.get("/api/calls/stats", headers=rep_headers)
    assert response.status_code == 200
    assert response.json()["total_calls"] == 1


def test_health_no_auth_required(client):
    response = client.get("/api/health")
    assert response.status_code == 200

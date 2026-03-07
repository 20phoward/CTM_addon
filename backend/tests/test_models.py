from database import Call, CallScore, ConversionStatus
from models.schemas import CallScoreResponse, CallSummary


def test_call_score_creation(db):
    call = Call(status="completed")
    db.add(call)
    db.commit()

    score = CallScore(
        call_id=call.id,
        rep_score=8.0, rep_tone=9.0, rep_steering=7.0, rep_service=8.0,
        rep_reasoning="Good call handling",
        lead_score=7.0, lead_service_match=8.0, lead_insurance=5.0, lead_intent=8.0,
        lead_reasoning="Strong intent for treatment",
    )
    db.add(score)
    db.commit()

    assert score.id is not None
    assert score.rep_score == 8.0
    assert score.lead_reasoning == "Strong intent for treatment"


def test_conversion_status_creation(db):
    call = Call(status="completed", gclid="test-gclid-123")
    db.add(call)
    db.commit()

    conversion = ConversionStatus(
        call_id=call.id, gclid="test-gclid-123",
        lead_score=7.0, status="pending",
    )
    db.add(conversion)
    db.commit()

    assert conversion.id is not None
    assert conversion.status == "pending"


def test_call_relationships(db):
    call = Call(status="completed")
    db.add(call)
    db.commit()

    score = CallScore(call_id=call.id, rep_score=8.0, lead_score=7.0)
    conversion = ConversionStatus(call_id=call.id, status="sent")
    db.add_all([score, conversion])
    db.commit()

    db.refresh(call)
    assert call.score is not None
    assert call.conversion is not None
    assert call.score.rep_score == 8.0
    assert call.conversion.status == "sent"


def test_call_cascade_delete(db):
    call = Call(status="completed")
    db.add(call)
    db.commit()

    db.add(CallScore(call_id=call.id, rep_score=8.0, lead_score=7.0))
    db.add(ConversionStatus(call_id=call.id, status="pending"))
    db.commit()

    db.delete(call)
    db.commit()

    assert db.query(CallScore).count() == 0
    assert db.query(ConversionStatus).count() == 0


def test_call_score_response_schema():
    data = CallScoreResponse(
        id=1, call_id=1, rep_score=8.0, rep_tone=9.0,
        rep_steering=7.0, rep_service=8.0, rep_reasoning="Good",
        lead_score=7.0, lead_service_match=8.0,
        lead_insurance=5.0, lead_intent=8.0, lead_reasoning="Strong",
    )
    assert data.rep_score == 8.0
    assert data.lead_score == 7.0


def test_call_summary_schema():
    summary = CallSummary(
        id=1, status="completed", source_type="webhook",
        campaign_name="Rehab Campaign", rep_score=8.0, lead_score=7.0,
    )
    assert summary.campaign_name == "Rehab Campaign"
    assert summary.rep_score == 8.0

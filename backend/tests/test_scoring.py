import json
from unittest.mock import patch, MagicMock
from services.scoring import score_call, parse_scoring_response


def test_parse_scoring_response_valid():
    raw = json.dumps({
        "rep_score": 8, "rep_tone": 9, "rep_steering": 7, "rep_service": 8,
        "rep_reasoning": "Agent was professional and warm.",
        "lead_score": 7, "lead_service_match": 9, "lead_insurance": 5, "lead_intent": 7,
        "lead_reasoning": "Caller asked about inpatient rehab.",
    })
    result = parse_scoring_response(raw)
    assert result is not None
    assert result["rep_score"] == 8
    assert result["lead_score"] == 7
    assert result["rep_reasoning"] == "Agent was professional and warm."
    assert result["lead_insurance"] == 5


def test_parse_scoring_response_with_code_fences():
    raw = "```json\n" + json.dumps({
        "rep_score": 8, "rep_tone": 9, "rep_steering": 7, "rep_service": 8,
        "rep_reasoning": "Good.", "lead_score": 7, "lead_service_match": 9,
        "lead_insurance": 5, "lead_intent": 7, "lead_reasoning": "Strong.",
    }) + "\n```"
    result = parse_scoring_response(raw)
    assert result is not None
    assert result["rep_score"] == 8


def test_parse_scoring_response_invalid_json():
    result = parse_scoring_response("not json at all")
    assert result is None


def test_score_call_returns_scores():
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps({
        "rep_score": 8, "rep_tone": 9, "rep_steering": 7, "rep_service": 8,
        "rep_reasoning": "Good.", "lead_score": 7, "lead_service_match": 9,
        "lead_insurance": 5, "lead_intent": 7, "lead_reasoning": "Strong.",
    })

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("services.scoring.anthropic.Anthropic", return_value=mock_client):
        result = score_call(
            transcript_text="Hello, I need help with rehab.",
            segments=[{"start": 0.0, "end": 2.0, "text": "Hello, I need help with rehab."}],
            call_metadata={"duration": 120, "campaign_name": "Rehab Ads", "keyword": "inpatient rehab", "landing_page_url": "https://example.com/rehab"},
        )

    assert result is not None
    assert result["rep_score"] == 8
    assert result["lead_score"] == 7


def test_score_call_no_api_key():
    with patch("services.scoring.ANTHROPIC_API_KEY", ""):
        result = score_call(
            transcript_text="Hello",
            segments=[{"start": 0.0, "end": 1.0, "text": "Hello"}],
            call_metadata={},
        )
    assert result is None

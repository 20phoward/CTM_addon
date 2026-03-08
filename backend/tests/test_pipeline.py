from unittest.mock import patch, MagicMock
from pathlib import Path
from database import Call, CallScore, Transcript
from services.pipeline import process_call


def test_pipeline_creates_score_and_transcript(db):
    call = Call(audio_filename="test.wav", status="pending")
    db.add(call)
    db.commit()

    mock_tx = {
        "full_text": "Hello, how are you?",
        "segments": [{"start": 0.0, "end": 2.0, "text": "Hello, how are you?"}],
        "duration": 2.0,
    }

    mock_wav_path = MagicMock(spec=Path)
    mock_wav_path.exists.return_value = True

    with patch("services.pipeline.convert_to_wav", return_value=mock_wav_path), \
         patch("services.pipeline.transcribe_audio", return_value=mock_tx), \
         patch("services.pipeline.score_call", return_value=None), \
         patch("services.pipeline.STORAGE_DIR", new_callable=lambda: MagicMock(spec=Path)) as mock_dir:

        mock_dir.__truediv__ = MagicMock(return_value=mock_wav_path)

        from services.pipeline import process_call
        process_call(call.id, db)

    db.refresh(call)
    assert call.status == "completed"
    assert call.transcript is not None
    assert call.transcript.full_text == "Hello, how are you?"
    assert call.score is not None
    assert call.duration == 2.0


def test_pipeline_calls_scoring_service(db):
    call = Call(audio_filename="test.wav", status="pending",
                campaign_name="Rehab Ads", keyword="inpatient rehab",
                landing_page_url="https://example.com")
    db.add(call)
    db.commit()

    mock_tx = {
        "full_text": "Hello, I need help with rehab.",
        "segments": [{"start": 0.0, "end": 2.0, "text": "Hello, I need help with rehab."}],
        "duration": 120.0,
    }
    mock_scores = {
        "rep_score": 8.0, "rep_tone": 9.0, "rep_steering": 7.0, "rep_service": 8.0,
        "rep_reasoning": "Good call handling.",
        "lead_score": 7.0, "lead_service_match": 9.0, "lead_insurance": 5.0, "lead_intent": 7.0,
        "lead_reasoning": "Strong intent for treatment.",
    }

    mock_wav_path = MagicMock(spec=Path)
    mock_wav_path.exists.return_value = True

    with patch("services.pipeline.convert_to_wav", return_value=mock_wav_path), \
         patch("services.pipeline.transcribe_audio", return_value=mock_tx), \
         patch("services.pipeline.score_call", return_value=mock_scores) as mock_score, \
         patch("services.pipeline.STORAGE_DIR", new_callable=lambda: MagicMock(spec=Path)) as mock_dir:

        mock_dir.__truediv__ = MagicMock(return_value=mock_wav_path)

        from services.pipeline import process_call
        process_call(call.id, db)

    db.refresh(call)
    assert call.status == "completed"
    assert call.score is not None
    assert call.score.rep_score == 8.0
    assert call.score.lead_score == 7.0
    assert call.score.rep_reasoning == "Good call handling."
    assert call.score.lead_reasoning == "Strong intent for treatment."
    mock_score.assert_called_once()


def test_pipeline_handles_missing_file(db):
    call = Call(audio_filename="nonexistent.wav", status="pending")
    db.add(call)
    db.commit()

    with patch("services.pipeline.STORAGE_DIR", new_callable=lambda: MagicMock(spec=Path)) as mock_dir:
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False
        mock_dir.__truediv__ = MagicMock(return_value=mock_path)

        from services.pipeline import process_call
        process_call(call.id, db)

    db.refresh(call)
    assert call.status == "failed"
    assert "not found" in call.error_message


def test_pipeline_handles_scoring_failure(db):
    call = Call(audio_filename="test.wav", status="pending")
    db.add(call)
    db.commit()

    mock_tx = {
        "full_text": "Hello",
        "segments": [{"start": 0.0, "end": 1.0, "text": "Hello"}],
        "duration": 1.0,
    }

    mock_wav_path = MagicMock(spec=Path)
    mock_wav_path.exists.return_value = True

    with patch("services.pipeline.convert_to_wav", return_value=mock_wav_path), \
         patch("services.pipeline.transcribe_audio", return_value=mock_tx), \
         patch("services.pipeline.score_call", return_value=None), \
         patch("services.pipeline.STORAGE_DIR", new_callable=lambda: MagicMock(spec=Path)) as mock_dir:

        mock_dir.__truediv__ = MagicMock(return_value=mock_wav_path)

        from services.pipeline import process_call
        process_call(call.id, db)

    db.refresh(call)
    assert call.status == "completed"
    assert call.score is not None
    assert call.score.rep_score is None


def test_pipeline_creates_conversion_when_gclid_present(tmp_path, db):
    """Pipeline should create ConversionStatus after scoring if GCLID exists."""
    from database import ConversionStatus

    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake-wav-data")

    call = Call(
        source_type="ctm_webhook",
        audio_filename=str(audio),
        status="pending",
        gclid="test-gclid-pipeline",
    )
    db.add(call)
    db.commit()

    with patch("services.pipeline.STORAGE_DIR", tmp_path), \
         patch("services.pipeline.convert_to_wav", return_value=audio), \
         patch("services.pipeline.transcribe_audio", return_value={
             "full_text": "Hello", "segments": [], "duration": 30.0
         }), \
         patch("services.pipeline.score_call", return_value={
             "rep_score": 7.0, "lead_score": 8.5,
             "rep_tone": 7.0, "rep_steering": 7.0, "rep_service": 7.0, "rep_reasoning": "Good",
             "lead_service_match": 9.0, "lead_insurance": 8.0, "lead_intent": 9.0, "lead_reasoning": "Strong",
         }), \
         patch("services.pipeline.upload_conversion", return_value={
             "status": "sent (dry_run)", "gclid": "test-gclid-pipeline",
             "conversion_value": 8.5, "error": None,
         }):
        process_call(call.id, db)

    conv = db.query(ConversionStatus).filter(ConversionStatus.call_id == call.id).first()
    assert conv is not None
    assert conv.gclid == "test-gclid-pipeline"
    assert conv.lead_score == 8.5
    assert "sent" in conv.status


def test_pipeline_skips_conversion_when_no_gclid(tmp_path, db):
    """Pipeline should not create ConversionStatus if no GCLID."""
    from database import ConversionStatus

    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake-wav-data")

    call = Call(
        source_type="manual_upload",
        audio_filename=str(audio),
        status="pending",
    )
    db.add(call)
    db.commit()

    with patch("services.pipeline.STORAGE_DIR", tmp_path), \
         patch("services.pipeline.convert_to_wav", return_value=audio), \
         patch("services.pipeline.transcribe_audio", return_value={
             "full_text": "Hello", "segments": [], "duration": 30.0
         }), \
         patch("services.pipeline.score_call", return_value={
             "rep_score": 7.0, "lead_score": 8.5,
             "rep_tone": 7.0, "rep_steering": 7.0, "rep_service": 7.0, "rep_reasoning": "Good",
             "lead_service_match": 9.0, "lead_insurance": 8.0, "lead_intent": 9.0, "lead_reasoning": "Strong",
         }):
        process_call(call.id, db)

    conv = db.query(ConversionStatus).filter(ConversionStatus.call_id == call.id).first()
    assert conv is None

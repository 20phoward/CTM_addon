from unittest.mock import patch, MagicMock
from pathlib import Path
from database import Call, CallScore, Transcript


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
         patch("services.pipeline.STORAGE_DIR", new_callable=lambda: MagicMock(spec=Path)) as mock_dir:

        mock_dir.__truediv__ = MagicMock(return_value=mock_wav_path)

        from services.pipeline import process_call
        process_call(call.id, db)

    db.refresh(call)
    assert call.status == "completed"
    assert call.transcript is not None
    assert call.transcript.full_text == "Hello, how are you?"
    assert call.score is not None  # placeholder score created
    assert call.duration == 2.0


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

import logging
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from config import STORAGE_DIR
from database import Call, Transcript, CallScore
from services.transcription import transcribe_audio
from services.scoring import score_call

logger = logging.getLogger(__name__)


def convert_to_wav(input_path: Path) -> Path:
    """Convert any audio file to 16kHz mono WAV for Whisper."""
    wav_path = input_path.with_suffix(".wav")
    if input_path.suffix.lower() == ".wav":
        return input_path
    logger.info("Converting %s -> %s", input_path.name, wav_path.name)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            str(wav_path),
        ],
        capture_output=True,
        check=True,
    )
    return wav_path


def process_call(call_id: int, db: Session):
    """Full processing pipeline: transcode -> transcribe -> score -> store."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        logger.error("Call %d not found", call_id)
        return

    try:
        call.status = "processing"
        db.commit()

        audio_path = STORAGE_DIR / call.audio_filename
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Transcode
        wav_path = convert_to_wav(audio_path)

        # Transcribe
        logger.info("Transcribing call %d", call_id)
        tx_result = transcribe_audio(wav_path)

        transcript = Transcript(
            call_id=call_id,
            full_text=tx_result["full_text"],
            segments=tx_result["segments"],
        )
        db.add(transcript)
        call.duration = tx_result["duration"]
        db.commit()

        # Score with Claude AI
        logger.info("Scoring call %d", call_id)
        call_metadata = {
            "duration": call.duration,
            "campaign_name": call.campaign_name,
            "keyword": call.keyword,
            "landing_page_url": call.landing_page_url,
        }
        scores = score_call(tx_result["full_text"], tx_result["segments"], call_metadata)

        if scores:
            call_score = CallScore(call_id=call_id, **scores)
        else:
            call_score = CallScore(call_id=call_id)
        db.add(call_score)

        call.status = "completed"
        db.commit()
        logger.info("Call %d processing completed", call_id)

    except Exception as e:
        logger.exception("Processing failed for call %d", call_id)
        call.status = "failed"
        call.error_message = str(e)
        db.commit()

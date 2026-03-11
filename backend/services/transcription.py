import logging
from pathlib import Path

from openai import OpenAI

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def transcribe_audio(audio_path: Path) -> dict:
    """Transcribe an audio file using OpenAI Whisper API.

    Returns:
        dict with keys:
            - full_text: str
            - segments: list of {start, end, text}
            - duration: float (total seconds)
    """
    client = _get_client()
    logger.info("Transcribing via OpenAI Whisper API: %s", audio_path)

    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = []
    for seg in getattr(result, "segments", []) or []:
        start = seg.start if hasattr(seg, "start") else seg["start"]
        end = seg.end if hasattr(seg, "end") else seg["end"]
        text = seg.text if hasattr(seg, "text") else seg["text"]
        segments.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "text": text.strip(),
            "speaker": None,
        })

    duration = segments[-1]["end"] if segments else getattr(result, "duration", 0.0)

    return {
        "full_text": result.text.strip(),
        "segments": segments,
        "duration": duration,
    }


def merge_speaker_segments(
    worker_segments: list[dict],
    patient_segments: list[dict],
    worker_name: str,
    patient_name: str,
) -> list[dict]:
    """Merge two lists of transcript segments with speaker labels, sorted by start time."""
    merged = []
    for seg in worker_segments:
        merged.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
            "speaker": worker_name,
        })
    for seg in patient_segments:
        merged.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
            "speaker": patient_name,
        })
    merged.sort(key=lambda s: s["start"])
    return merged

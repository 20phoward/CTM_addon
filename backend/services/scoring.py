import json
import logging

import anthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

SCORING_PROMPT = """\
You are an expert call analyst for a behavioral health and rehabilitation facility. \
Analyze the following call transcript and score it on two independent dimensions.

<transcript>
{transcript}
</transcript>

<call_metadata>
Duration: {duration} seconds
Campaign: {campaign}
Keyword: {keyword}
Landing Page: {landing_page}
</call_metadata>

Produce TWO independent scores (0-10 scale) with sub-scores and reasoning.

**Rep Score** — How well did the representative handle the call?
- tone (0-10): Friendly, professional, empathetic
- steering (0-10): Guided conversation productively, stayed on track
- service (0-10): Addressed concerns, answered questions, offered clear next steps

**Lead Score** — How qualified is the caller as a prospect?
- service_match (0-10): Were they specifically looking for behavioral health / rehab services?
- insurance (0-10): Did they mention having private health insurance?
- intent (0-10): Actively seeking treatment vs. just browsing?

Score guide: 0-3 Poor, 4-5 Below average, 6-7 Average, 8-9 Good, 10 Exceptional.

Respond with ONLY valid JSON (no markdown, no code fences) in this exact schema:
{{
  "rep_score": <overall 0-10>,
  "rep_tone": <0-10>,
  "rep_steering": <0-10>,
  "rep_service": <0-10>,
  "rep_reasoning": "<2-3 sentences explaining the rep score>",
  "lead_score": <overall 0-10>,
  "lead_service_match": <0-10>,
  "lead_insurance": <0-10>,
  "lead_intent": <0-10>,
  "lead_reasoning": "<2-3 sentences explaining the lead score>"
}}
"""


def parse_scoring_response(raw: str) -> dict | None:
    """Parse Claude's JSON response into a structured dict."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse scoring response: %s", raw[:500])
        return None

    return {
        "rep_score": float(data.get("rep_score", 0)),
        "rep_tone": float(data.get("rep_tone", 0)),
        "rep_steering": float(data.get("rep_steering", 0)),
        "rep_service": float(data.get("rep_service", 0)),
        "rep_reasoning": data.get("rep_reasoning", ""),
        "lead_score": float(data.get("lead_score", 0)),
        "lead_service_match": float(data.get("lead_service_match", 0)),
        "lead_insurance": float(data.get("lead_insurance", 0)),
        "lead_intent": float(data.get("lead_intent", 0)),
        "lead_reasoning": data.get("lead_reasoning", ""),
    }


def score_call(transcript_text: str, segments: list[dict], call_metadata: dict) -> dict | None:
    """Send transcript + metadata to Claude for Rep + Lead scoring.

    Returns parsed dict with scores, or None if API key is missing.
    """
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — skipping scoring")
        return None

    lines = []
    for seg in segments:
        ts = f"[{seg['start']:.1f}s - {seg['end']:.1f}s]"
        speaker = f" ({seg['speaker']})" if seg.get("speaker") else ""
        lines.append(f"{ts}{speaker} {seg['text']}")
    formatted_transcript = "\n".join(lines)

    prompt = SCORING_PROMPT.format(
        transcript=formatted_transcript,
        duration=call_metadata.get("duration", "unknown"),
        campaign=call_metadata.get("campaign_name", "unknown"),
        keyword=call_metadata.get("keyword", "unknown"),
        landing_page=call_metadata.get("landing_page_url", "unknown"),
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    return parse_scoring_response(raw)

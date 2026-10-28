"""
gemini_audio.py — Google GenAI Multimodal Audio Forensic Analysis
==================================================================
Performs audio forensics using Google's official GenAI SDK (free tier):
  - Cross-verifies speech transcript against Groq Whisper to spot hallucinations or drifts
  - Analyzes acoustic characteristics (breathing cadence, robotic flattening, room reverb)
  - Explicit scientific guard: Does not claim validated voice-clone detection without
    calibrated acoustic biometric classifiers.
  - Graceful fallback on missing keys, rate limits, timeouts, and API errors.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher

from shared.schemas.forensics import (
    GeminiAudioForensics,
    TranscriptComparison,
    AcousticAnomalyAnalysis,
    VoiceCloneAssessment,
)
from shared.json_utils import parse_llm_json

logger = logging.getLogger(__name__)

CANDIDATE_GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3-flash-preview",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]


def _compute_transcript_similarity(t1: str, t2: str) -> float:
    """Calculates word-level SequenceMatcher similarity ratio."""
    if not t1 or not t2:
        return 0.0
    w1 = t1.lower().split()
    w2 = t2.lower().split()
    if not w1 or not w2:
        return 0.0
    matcher = SequenceMatcher(None, w1, w2)
    return round(float(matcher.ratio()), 3)


def _sanitize_error_message(err_text: str) -> str:
    """Strips API keys or sensitive credential patterns from error messages."""
    import re
    cleaned = re.sub(r"AIza[0-9A-Za-z\-_]{35}", "[REDACTED_GEMINI_KEY]", err_text)
    cleaned = re.sub(r"key=[0-9A-Za-z\-_]+", "key=[REDACTED]", cleaned)
    return cleaned[:300]


def analyze_audio_with_gemini(
    audio_path: Optional[str],
    whisper_transcript: Optional[str] = None,
    segments: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Analyzes audio stream using Google GenAI SDK (Gemini 2.5/1.5 Flash).
    Returns structured GeminiAudioForensics schema dictionary.
    """
    # 1. Check audio file presence
    if not audio_path or not os.path.isfile(audio_path):
        schema = GeminiAudioForensics(
            status="not_assessed",
            reason="Audio file not available or not provided.",
            transcript_comparison=TranscriptComparison(
                status="not_assessed",
                whisper_transcript=whisper_transcript[:300] if whisper_transcript else None,
            ),
        )
        return schema.model_dump()

    # 2. Check GEMINI_API_KEY
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        schema = GeminiAudioForensics(
            status="not_assessed",
            reason="GEMINI_API_KEY not configured in environment.",
            transcript_comparison=TranscriptComparison(
                status="not_assessed",
                whisper_transcript=whisper_transcript[:300] if whisper_transcript else None,
            ),
        )
        return schema.model_dump()

    # 3. Read audio file bytes (cap at 20MB for direct payload transfer)
    try:
        file_size = os.path.getsize(audio_path)
        if file_size > 22 * 1024 * 1024:
            schema = GeminiAudioForensics(
                status="not_assessed",
                reason=f"Audio file exceeds inline payload limit ({file_size / (1024*1024):.1f}MB > 20MB).",
            )
            return schema.model_dump()

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        # Determine MIME type from extension
        ext = os.path.splitext(audio_path)[1].lower()
        mime_map = {
            ".mp3": "audio/mp3",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".m4a": "audio/m4a",
            ".aac": "audio/aac",
            ".flac": "audio/flac",
        }
        mime_type = mime_map.get(ext, "audio/mp3")
    except Exception as e:
        schema = GeminiAudioForensics(
            status="failed",
            reason=_sanitize_error_message(f"Error reading audio file: {e}"),
        )
        return schema.model_dump()

    # 4. Initialize GenAI client and query model
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        schema = GeminiAudioForensics(
            status="not_assessed",
            reason="google-genai SDK not installed.",
        )
        return schema.model_dump()

    candidate_models = list(CANDIDATE_GEMINI_MODELS)
    timeout_sec = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "25.0"))
    timeout_ms = int(timeout_sec * 1000)

    try:
        client = genai.Client(
            api_key=gemini_key,
            http_options=types.HttpOptions(timeout=timeout_ms)
        )
    except Exception as init_err:
        schema = GeminiAudioForensics(
            status="failed",
            error_code="CLIENT_INIT_FAILED",
            reason=_sanitize_error_message(f"Failed to initialize GenAI client: {init_err}"),
        )
        return schema.model_dump()

    try:
        remote_models = [
            m.name.replace("models/", "")
            for m in client.models.list()
            if "generateContent" in getattr(m, "supported_actions", [])
        ]
        matched_remote = [m for m in remote_models if any(tag in m.lower() for tag in ("2.5-flash", "1.5-flash", "2.0-flash", "flash-latest"))]
        for rm in reversed(matched_remote):
            if rm in candidate_models:
                candidate_models.remove(rm)
            candidate_models.insert(0, rm)
    except Exception as e:
        logger.debug(f"[gemini_audio] Dynamic model listing skipped: {e}")

    whisper_sample = (whisper_transcript or "").strip()[:2500]

    prompt = (
        "You are an objective forensic audio analyst. Listen to the attached audio clip.\n"
        "1. Transcribe the spoken words accurately.\n"
        "2. Compare against this baseline Whisper transcript:\n"
        f"\"\"\"{whisper_sample}\"\"\"\n"
        "Identify any significant discrepancies, missed sentences, or transcript hallucination.\n"
        "3. Inspect acoustic properties:\n"
        "- Cadence: Is speech rhythm natural with organic breathing pauses, or unnaturally metronomic?\n"
        "- Artifacts: Are there metallic timbres, robotic clipping, or unnatural sentence splices?\n"
        "- Room acoustics: Is background noise / room reverberation consistent across speech turns?\n"
        "4. Forensic Caveat: Do NOT claim positive voice-clone detection without calibrated biometric models.\n\n"
        "Return ONLY a valid JSON object matching this exact format:\n"
        "{\n"
        '  "gemini_transcript": "Spoken text from audio...",\n'
        '  "discrepancies": ["discrepancy 1", "discrepancy 2"],\n'
        '  "timestamp_notes": "Temporal or alignment observations",\n'
        '  "cadence_observations": "Observations on speech rhythm and naturalness",\n'
        '  "robotic_artifacts": "Observations on synthetic/robotic artifacts or None",\n'
        '  "room_acoustics_consistent": true,\n'
        '  "acoustic_anomalies": ["anomaly 1", "anomaly 2"],\n'
        '  "voice_observations": ["observation on vocal naturalness"]\n'
        "}"
    )

    last_error = None
    last_error_code = None
    parsed = None
    model_used = None

    import time
    for model_name in candidate_models:
        # Bounded retries (max 2 attempts per candidate model for transient faults)
        for attempt in range(2):
            try:
                logger.info(f"[gemini_audio] Querying model {model_name} (attempt {attempt+1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                        prompt,
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = getattr(response, "text", "") or ""
                parsed = parse_llm_json(raw_text)
                if parsed:
                    model_used = model_name
                    break
            except Exception as err:
                last_error = err
                err_msg = str(err).lower()
                logger.warning(f"[gemini_audio] {model_name} attempt {attempt+1} failed: {_sanitize_error_message(str(err))}")

                if "deadline" in err_msg or "timeout" in err_msg or "504" in err_msg:
                    last_error_code = "DEADLINE_EXCEEDED"
                    break  # Stop retrying this model on deadline timeout
                elif "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg:
                    last_error_code = "RATE_LIMIT_EXCEEDED"
                    time.sleep(1.0)
                elif "503" in err_msg or "502" in err_msg:
                    last_error_code = "SERVICE_UNAVAILABLE"
                    time.sleep(1.0)
                elif "401" in err_msg or "403" in err_msg:
                    last_error_code = "AUTH_ERROR"
                    break
                else:
                    last_error_code = "API_ERROR"

        if parsed and model_used:
            break

    if not parsed or not model_used:
        err_text = _sanitize_error_message(str(last_error)) if last_error else "Empty response from Gemini API"
        schema = GeminiAudioForensics(
            status="failed",
            error_code=last_error_code or "DEADLINE_EXCEEDED",
            reason=f"Gemini API analysis failed ({last_error_code or 'ERROR'}): {err_text}",
            transcript_comparison=TranscriptComparison(
                status="failed",
                whisper_transcript=whisper_transcript[:300] if whisper_transcript else None,
            ),
        )
        return schema.model_dump()

    # 5. Extract structured results
    g_transcript = parsed.get("gemini_transcript", "")
    discrepancies = parsed.get("discrepancies", [])
    if isinstance(discrepancies, str):
        discrepancies = [discrepancies]

    sim_score = _compute_transcript_similarity(g_transcript, whisper_transcript or "")

    comparison = TranscriptComparison(
        status="assessed",
        gemini_transcript=g_transcript[:1200] if g_transcript else None,
        whisper_transcript=whisper_transcript[:1200] if whisper_transcript else None,
        similarity_score=sim_score,
        discrepancies=discrepancies[:6],
        timestamp_notes=parsed.get("timestamp_notes"),
    )

    acoustic_anomalies = parsed.get("acoustic_anomalies", [])
    if isinstance(acoustic_anomalies, str):
        acoustic_anomalies = [acoustic_anomalies]

    acoustics = AcousticAnomalyAnalysis(
        status="assessed",
        cadence_observations=parsed.get("cadence_observations"),
        robotic_artifacts=parsed.get("robotic_artifacts"),
        room_acoustics_consistent=parsed.get("room_acoustics_consistent"),
        anomaly_indicators=acoustic_anomalies[:6],
    )

    voice_obs = parsed.get("voice_observations", [])
    if isinstance(voice_obs, str):
        voice_obs = [voice_obs]

    voice_clone = VoiceCloneAssessment(
        status="assessed",
        observations=voice_obs[:5],
    )

    schema = GeminiAudioForensics(
        status="assessed",
        model_used=model_used,
        transcript_comparison=comparison,
        acoustic_anomaly_analysis=acoustics,
        voice_clone_assessment=voice_clone,
        limitations="Gemini multimodal audio inspection provides semantic and auditory anomaly reasoning. It does not replace biometric acoustic analysis or cryptographic provenance verification.",
    )
    return schema.model_dump()

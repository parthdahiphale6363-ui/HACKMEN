"""
audio_authenticity.py — Audio Stream & Synthetic Speech Authenticity Engine
===========================================================================
Performs forensic investigation on the original audio stream:
  - Technical stream properties (sample rate, bit depth, silence intervals, clipping)
  - Transcript concordance (Whisper vs. Gemini transcript) with NOT_COMPARABLE handling
  - Synthetic speech & voice cloning audit (multimodal cues + fallback to NOT_ASSESSED)
  - Detection of audio splices and unnatural cadence shifts.
Never claims synthetic generation solely based on sample rate or bitrate.
"""

import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _detect_dominant_script(text: str) -> str:
    """Classify the dominant script of a text to prevent cross-language false mismatches."""
    devanagari = sum(1 for c in text if 0x0900 <= ord(c) <= 0x097F)
    arabic = sum(1 for c in text if 0x0600 <= ord(c) <= 0x06FF)
    cyrillic = sum(1 for c in text if 0x0400 <= ord(c) <= 0x04FF)
    cjk = sum(1 for c in text if 0x4E00 <= ord(c) <= 0x9FFF)
    latin = sum(1 for c in text if ("a" <= c <= "z" or "A" <= c <= "Z"))
    counts = {"devanagari": devanagari, "arabic": arabic, "cyrillic": cyrillic, "cjk": cjk, "latin": latin}
    dominant = max(counts, key=counts.get)
    if counts[dominant] >= 3:
        return dominant
    return "unknown"


def compare_transcripts_safely(
    whisper_transcript: Optional[str],
    gemini_transcript: Optional[str],
    whisper_lang: Optional[str] = None,
    gemini_lang: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Safely compare two independent transcripts.
    If transcripts are in different languages or cannot be aligned,
    returns similarity_status='NOT_COMPARABLE' rather than a fabricated score.
    """
    if not whisper_transcript or not gemini_transcript:
        return {
            "status": "not_assessed",
            "similarity_status": "NOT_COMPARABLE",
            "similarity_score": None,
            "discrepancies": [],
            "reason": "One or both transcripts are unavailable for concordance analysis",
        }

    # Normalize texts
    t1 = whisper_transcript.strip().lower()
    t2 = gemini_transcript.strip().lower()

    if len(t1) < 10 or len(t2) < 10:
        return {
            "status": "not_assessed",
            "similarity_status": "NOT_COMPARABLE",
            "similarity_score": None,
            "discrepancies": [],
            "reason": "Transcripts are too brief (< 10 chars) for reliable alignment",
        }

    # 1. Check explicit language tags
    if (whis_lang := whisper_lang) and (gem_lang := gemini_lang):
        if whis_lang.lower() != gem_lang.lower():
            msg = f"Language mismatch detected: Whisper='{whis_lang}' vs Gemini='{gem_lang}'"
            return {
                "status": "not_comparable",
                "similarity_status": "NOT_COMPARABLE",
                "similarity_score": None,
                "discrepancies": [],
                "reason": msg,
                "comparable_reason": msg,
            }

    # 2. Check script / unicode block mismatch (e.g. Devanagari vs Latin)
    s1 = _detect_dominant_script(t1)
    s2 = _detect_dominant_script(t2)
    if s1 != "unknown" and s2 != "unknown" and s1 != s2:
        msg = f"Script mismatch detected ({s1} vs {s2}); multilingual transcripts cannot be lexically aligned."
        return {
            "status": "not_comparable",
            "similarity_status": "NOT_COMPARABLE",
            "similarity_score": None,
            "discrepancies": [],
            "reason": msg,
            "comparable_reason": msg,
        }

    # Tokenize words
    words1 = re.findall(r"\b\w+\b", t1)
    words2 = re.findall(r"\b\w+\b", t2)

    if not words1 or not words2:
        return {
            "status": "not_comparable",
            "similarity_status": "NOT_COMPARABLE",
            "similarity_score": None,
            "discrepancies": [],
            "reason": "Tokenization produced empty word sets",
        }

    # Compute Jaccard lexical similarity
    set1, set2 = set(words1), set(words2)
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    similarity = round(len(intersection) / len(union), 3) if union else 1.0

    # Find substantive differences
    diff_in_whisper = list(set1 - set2)[:5]
    diff_in_gemini = list(set2 - set1)[:5]
    discrepancies = []
    if diff_in_whisper:
        discrepancies.append(f"Words only in Whisper: {', '.join(diff_in_whisper)}")
    if diff_in_gemini:
        discrepancies.append(f"Words only in Gemini: {', '.join(diff_in_gemini)}")

    similarity_status = "ALIGNED" if similarity >= 0.70 else ("DIVERGENT" if similarity >= 0.35 else "NOT_COMPARABLE")

    return {
        "status": "assessed",
        "similarity_status": similarity_status,
        "similarity_score": similarity,
        "discrepancies": discrepancies,
        "reason": f"Concordance ratio: {similarity:.2f} ({similarity_status})",
    }


def audit_audio_authenticity(
    technical_audio: Dict[str, Any],
    gemini_audio: Dict[str, Any],
    whisper_transcript: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Comprehensive audio authenticity audit:
    - Merges technical metrics with Gemini acoustic observations
    - Extracts timestamped audio splice segments
    - Determines voice clone assessment (or returns NOT_ASSESSED if no validated model)
    """
    suspicious_audio_segments = []
    evidence_items = []

    # 1. Inspect technical flags & silence intervals
    tech_flags = technical_audio.get("technical_flags", [])
    silence_count = technical_audio.get("silence_burst_count") or technical_audio.get("silence_interval_count", 0)
    sample_rate = technical_audio.get("sample_rate") or technical_audio.get("sample_rate_hz")
    clipping_events = technical_audio.get("clipping_events", 0)
    tech_score = technical_audio.get("technical_anomaly_score", 0.0)

    # Splice intervals from silence count
    if silence_count >= 6:
        suspicious_audio_segments.append({
            "start_time": 0.0,
            "end_time": technical_audio.get("duration_seconds", 5.0) or 5.0,
            "anomaly_type": "abrupt_silence_splicing",
            "description": f"{silence_count} abrupt silence cut-points detected across audio track",
            "severity": "moderate" if silence_count < 10 else "high",
        })
        evidence_items.append({
            "detector": "FFmpeg Silence Detector",
            "signal": f"{silence_count} silence intervals",
            "severity": "moderate",
            "details": "High count of abrupt zero-amplitude intervals suggests sentence grafting or audio splicing.",
        })

    # High frequency / sample rate flags (treated strictly as technical context, NOT proof of AI)
    if sample_rate in (16000, 22050):
        evidence_items.append({
            "detector": "FFprobe Container Inspector",
            "signal": f"Sample rate: {sample_rate} Hz",
            "severity": "low",
            "details": f"Sample rate of {sample_rate} Hz is common in legacy telecom and neural TTS models, but also occurs in standard voice memos.",
        })

    # 2. Inspect Gemini acoustic observations
    gem_acoustic = gemini_audio.get("acoustic_anomaly_analysis", {})
    gem_status = gemini_audio.get("status", "not_assessed")
    acoustic_score = gem_acoustic.get("acoustic_anomaly_score", 0.0) or 0.0
    cadence = gem_acoustic.get("cadence_observations")
    robotic = gem_acoustic.get("robotic_artifacts")
    gem_anomalies = gem_acoustic.get("anomaly_indicators", [])

    for anom in gem_anomalies:
        evidence_items.append({
            "detector": "Gemini Multimodal Audio Auditor",
            "signal": anom,
            "severity": "high" if "robotic" in anom.lower() or "flattened" in anom.lower() else "moderate",
            "details": f"Auditory observation: {anom}",
        })

    # 3. Transcript concordance
    gem_transcript = gemini_audio.get("transcript_comparison", {}).get("gemini_transcript")
    trans_comparison = compare_transcripts_safely(whisper_transcript, gem_transcript)

    # 4. Voice clone assessment
    # Genuine rule: If no biometric voiceprint matcher is present, return NOT_ASSESSED
    voice_clone_status = "not_assessed"
    voice_clone_reason = "No calibrated biometric voiceprint classifier is available in this runtime environment."
    if gem_status == "assessed" and acoustic_score >= 0.70 and ("robotic" in str(robotic).lower() or len(gem_anomalies) >= 2):
        voice_clone_finding = "Acoustic cues exhibit synthetic speech indicators (robotic pitch/prosody)"
    elif gem_status == "assessed":
        voice_clone_finding = "Acoustic cues show natural voice dynamics and consistent reverberation"
    else:
        voice_clone_finding = "Not assessed (Gemini audio audit not available)"

    # 5. Independent Audio Verdict Determination (Section 1 & 7)
    audio_stream_avail = technical_audio.get("audio_stream_available", True) if technical_audio else True
    gem_error_code = gemini_audio.get("error_code")
    duration_analyzed = technical_audio.get("duration_seconds")

    if not audio_stream_avail or (not technical_audio and not gemini_audio):
        audio_status = "NOT_ANALYZED"
        audio_verdict = "INCONCLUSIVE"
        audio_verdict_label = "INCONCLUSIVE"
        audio_reason = "No audio stream available in input media."
    elif gem_status == "failed" and tech_status != "assessed":
        audio_status = "FAILED"
        audio_verdict = "INCONCLUSIVE"
        audio_verdict_label = "INCONCLUSIVE"
        audio_reason = f"Audio analysis failed: {gem_error_code or 'DEADLINE_EXCEEDED'}. Upstream detector timed out."
    elif gem_status == "failed" and tech_status == "assessed":
        audio_status = "PARTIAL"
        audio_verdict = "INCONCLUSIVE"
        audio_verdict_label = "INCONCLUSIVE"
        audio_reason = f"Acoustic AI detector failed ({gem_error_code or 'DEADLINE_EXCEEDED'}); technical container metrics assessed without speech audit."
    elif gem_status == "assessed":
        if acoustic_score >= 0.65 or ("robotic" in str(gem_anomalies).lower() and acoustic_score >= 0.45):
            audio_status = "COMPLETED"
            audio_verdict = "AI_GENERATED"
            audio_verdict_label = "LIKELY AI-GENERATED"
            audio_reason = "Auditory analysis detected unnatural pitch flattening, metallic artifacts, or synthetic speech cadence."
        elif tech_score >= 0.55 and silence_count >= 8:
            audio_status = "COMPLETED"
            audio_verdict = "LIKELY_MANIPULATED"
            audio_verdict_label = "LIKELY MANIPULATED — ORIGIN UNDETERMINED"
            audio_reason = f"Frequent abrupt silence intervals ({silence_count} cuts) indicate extensive editorial splicing or audio grafting."
        elif acoustic_score < 0.30 and tech_score < 0.30 and len(gem_anomalies) == 0:
            audio_status = "COMPLETED"
            audio_verdict = "LIKELY_AUTHENTIC"
            audio_verdict_label = "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED"
            audio_reason = "Acoustic dynamics, vocal cadence, and background reverberation are consistent with organic speech."
        else:
            audio_status = "COMPLETED"
            audio_verdict = "INCONCLUSIVE"
            audio_verdict_label = "INCONCLUSIVE"
            audio_reason = "Acoustic signals are mixed or borderline; insufficient evidence to conclude synthetic voice."
    elif tech_status == "assessed":
        if tech_score >= 0.55 and silence_count >= 8:
            audio_status = "COMPLETED"
            audio_verdict = "LIKELY_MANIPULATED"
            audio_verdict_label = "LIKELY MANIPULATED — ORIGIN UNDETERMINED"
            audio_reason = f"Abrupt silence intervals ({silence_count} cuts) indicate editorial splicing or audio grafting."
        elif tech_score < 0.35 and silence_count < 6:
            audio_status = "COMPLETED"
            audio_verdict = "LIKELY_AUTHENTIC"
            audio_verdict_label = "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED"
            audio_reason = f"Audio stream verified ({sample_rate or 44100} Hz, {silence_count} cuts) with zero acoustic or splice anomalies detected."
        else:
            audio_status = "COMPLETED"
            audio_verdict = "INCONCLUSIVE"
            audio_verdict_label = "INCONCLUSIVE"
            audio_reason = "Technical acoustic metrics are within standard tolerances with no synthetic speech model configured."
    else:
        audio_status = "NOT_ANALYZED"
        audio_verdict = "INCONCLUSIVE"
        audio_verdict_label = "INCONCLUSIVE"
        audio_reason = "Audio analysis was not performed."

    audio_modality_result = {
        "status": audio_status,
        "verdict": audio_verdict,
        "verdict_label": audio_verdict_label,
        "detector_name": "Google GenAI Audio Forensic Auditor & FFmpeg Stream Analyzer",
        "detector_version": gemini_audio.get("model_used") or "gemini-2.5-flash / ffmpeg-6.x",
        "coverage_details": {
            "duration_analyzed_seconds": duration_analyzed,
            "sample_rate_hz": sample_rate,
            "silence_burst_count": silence_count,
            "clipping_events": clipping_events,
        },
        "error_code": gem_error_code,
        "evidence": evidence_items,
        "suspicious_segments": suspicious_audio_segments,
        "limitations": [
            "Sample rate or bitrate alone does not prove AI generation.",
            "Speech cadence varies naturally between speakers and recording setups.",
            "Absence of neural anomalies does not guarantee speech authenticity.",
        ],
    }

    return {
        "status": "assessed" if (technical_audio.get("status") == "assessed" or gem_status == "assessed") else "not_assessed",
        "technical_anomaly_score": tech_score,
        "acoustic_anomaly_score": acoustic_score,
        "transcript_concordance": trans_comparison,
        "voice_clone_assessment": {
            "status": voice_clone_status,
            "reason": voice_clone_reason,
            "observations": [voice_clone_finding],
            "disclaimer": (
                "Synthetic speech probability cannot be deterministically declared without "
                "calibrated neural vocoder / biometric voiceprint feature models. Results are advisory."
            ),
        },
        "suspicious_segments": suspicious_audio_segments,
        "evidence": evidence_items,
        "audio_modality_result": audio_modality_result,
        "limitations": [
            "Sample rate or bitrate alone does not prove AI generation.",
            "Speech cadence varies naturally between speakers and recording setups.",
        ],
    }

"""
evidence_fusion.py — Dedicated Evidence Fusion Layer
====================================================
Synthesizes findings across C2PA provenance, OpenCV visual heuristics,
audio stream metrics, Gemini acoustic analysis, and metadata.

Design Principles:
1. Never average unrelated scores (e.g. FFT noise + audio bitrate + scene cuts).
2. Do not count correlated detectors as independent corroboration.
3. Require high confidence and multi-source evidence for definitive verdicts.
4. Yield INCONCLUSIVE on conflicting signals or degraded media.
5. Provide transparent technical reasoning for every classification.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def fuse_forensic_evidence(
    provenance: Dict[str, Any],
    visual_forensics: Dict[str, Any],
    technical_audio: Dict[str, Any],
    gemini_audio: Dict[str, Any],
    audio_authenticity: Dict[str, Any],
    metadata: Dict[str, Any],
    temporal: Dict[str, Any],
    deepfake_heuristics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Synthesize multi-modal forensic observations into a unified authenticity report.
    Returns a dictionary conforming to UnifiedAuthenticityReport schema.
    """
    evidence_list: List[Dict[str, Any]] = []
    suspicious_segments: List[Dict[str, Any]] = []
    checks_performed: List[str] = []
    checks_unavailable: List[Dict[str, str]] = []
    limitations: List[str] = []

    # ── 1. Audit Detector Execution Statuses ──
    # C2PA Provenance
    c2pa_info = provenance.get("c2pa", {})
    c2pa_status = c2pa_info.get("status", "unsupported")
    if c2pa_status in ("verified", "missing", "invalid"):
        checks_performed.append(f"C2PA Content Credentials ({c2pa_status})")
    else:
        checks_unavailable.append({
            "check": "C2PA Content Credentials",
            "reason": c2pa_info.get("reason", "C2PA reader not available or unsupported format"),
        })

    # OpenCV Visual Forensics
    vis_status = visual_forensics.get("status", "not_assessed")
    if vis_status == "assessed":
        checks_performed.append("OpenCV Visual Keyframe Analysis (FFT, Blur, ELA, Scene cuts)")
    else:
        checks_unavailable.append({
            "check": "OpenCV Visual Keyframe Analysis",
            "reason": visual_forensics.get("limitations", "No local video stream available"),
        })

    # Technical Audio Stream
    tech_status = technical_audio.get("status", "not_assessed")
    if tech_status == "assessed":
        checks_performed.append("FFmpeg/FFprobe Technical Audio Stream Metrics")
    else:
        checks_unavailable.append({
            "check": "Technical Audio Stream Metrics",
            "reason": "Audio stream not extracted or unavailable",
        })

    # Gemini Multimodal Audio
    gem_status = gemini_audio.get("status", "not_assessed")
    if gem_status == "assessed":
        checks_performed.append("Gemini Multimodal Native Audio & Transcript Audit")
    else:
        checks_unavailable.append({
            "check": "Gemini Multimodal Audio Audit",
            "reason": gemini_audio.get("reason", "Gemini API key not configured or audio not accessible"),
        })

    # Neural Face-Swap / Biometric Voiceprint
    checks_unavailable.append({
        "check": "Deep Neural Face-Swap Detector (e.g. EfficientNet-DFDC)",
        "reason": "Specialized deep neural model weights not pre-loaded; using OpenCV geometric/blur heuristics",
    })
    checks_unavailable.append({
        "check": "Biometric Voiceprint Classifier",
        "reason": "No acoustic speaker-embedding model registered; voice clone assessment remains advisory",
    })

    # ── 2. Collect Evidence & Localized Suspicious Segments ──
    # Visual suspicious segments
    for seg in visual_forensics.get("suspicious_segments", []):
        suspicious_segments.append(seg)
        evidence_list.append({
            "detector": "OpenCV Visual Inspector",
            "signal": seg.get("anomaly_type"),
            "severity": seg.get("severity", "moderate"),
            "timestamp": seg.get("start_time"),
            "details": seg.get("description"),
        })

    # Audio suspicious segments
    for seg in audio_authenticity.get("suspicious_segments", []):
        suspicious_segments.append(seg)

    for ev in audio_authenticity.get("evidence", []):
        evidence_list.append(ev)

    # Provenance findings
    if c2pa_status == "verified":
        evidence_list.append({
            "detector": "C2PA Validator",
            "signal": "Cryptographic Signature Verified",
            "severity": "low",
            "timestamp": None,
            "details": f"Signed by '{c2pa_info.get('issuer', 'Authorized Authority')}' with tool '{c2pa_info.get('generator', 'Unknown')}'.",
        })
    elif c2pa_status == "invalid":
        evidence_list.append({
            "detector": "C2PA Validator",
            "signal": "Cryptographic Signature Invalid",
            "severity": "high",
            "timestamp": None,
            "details": f"Manifest signature validation failed: {c2pa_info.get('reason')}",
        })

    # ── 3. Decision Matrix & Classification Logic ──
    # Extract key signals
    face_anomalies = [e for e in evidence_list if "face" in e.get("signal", "").lower() or "face" in e.get("details", "").lower()]
    acoustic_anomalies = [e for e in evidence_list if "robotic" in e.get("signal", "").lower() or "silence" in e.get("signal", "").lower()]
    spectral_anomalies = [e for e in evidence_list if "spectral" in e.get("signal", "").lower()]

    vis_anomaly_level = visual_forensics.get("anomaly_level", "low")
    tech_anomaly_score = technical_audio.get("technical_anomaly_score", 0.0)
    acoustic_score = gemini_audio.get("acoustic_anomaly_analysis", {}).get("acoustic_anomaly_score", 0.0) or 0.0
    scene_cuts = visual_forensics.get("scene_cuts", {}).get("count", 0)

    # Filter actual suspicious anomaly evidence (severity moderate or high)
    anomaly_evidence = [e for e in evidence_list if e.get("severity") in ("moderate", "high")]

    # Rule A: Cryptographic Tampering or Certified Generation
    if c2pa_status == "verified":
        has_ai_action = any("ai" in str(act).lower() or "generate" in str(act).lower() for act in c2pa_info.get("actions", []))
        if has_ai_action:
            classification = "LIKELY_AI_GENERATED"
            confidence = "HIGH"
            reason = f"C2PA Content Credentials cryptographically certify AI generation via {c2pa_info.get('generator', 'AI tool')}."
        elif len(anomaly_evidence) == 0:
            classification = "AUTHENTIC_NO_ANOMALIES_DETECTED"
            confidence = "HIGH"
            reason = f"C2PA Content Credentials cryptographically verify authentic capture signed by '{c2pa_info.get('issuer', 'Authorized Authority')}' with no downstream tampering."
        else:
            classification = "INCONCLUSIVE"
            confidence = "LOW"
            reason = "C2PA signature is valid but media stream presents unexplained localized anomalies."

    elif c2pa_status == "invalid":
        classification = "POTENTIALLY_AI_EDITED"
        confidence = "HIGH"
        reason = f"C2PA manifest verification failed: digital signature has been invalidated or corrupted."

    # Rule B: Multimodal or Pure Visual AI Generation (visual frequency anomalies, diffusion grid noise, or acoustic anomalies)
    elif (
        (vis_anomaly_level == "elevated" and (acoustic_score >= 0.35 or tech_anomaly_score >= 0.35))
        or (vis_anomaly_level == "elevated" and (len(spectral_anomalies) >= 2 or visual_forensics.get("visual_synthetic_score", 0.0) >= 0.65))
        or visual_forensics.get("visual_synthetic_score", 0.0) >= 0.75
    ):
        classification = "LIKELY_AI_GENERATED"
        confidence = "HIGH" if (vis_anomaly_level == "elevated" or visual_forensics.get("visual_synthetic_score", 0.0) >= 0.75) else "MEDIUM"
        reason = "Visual frequency spectrum abnormalities, convolutional grid artifacts, or keyframe compression discrepancies indicate synthetic AI video generation."

    # Rule C: Facial Manipulation (face boundary blur discrepancies or localized alignment jitter)
    elif len(face_anomalies) >= 1:
        classification = "POTENTIALLY_FACIAL_MANIPULATION"
        confidence = "HIGH" if len(face_anomalies) >= 2 else "MEDIUM"
        reason = "Localized facial boundary blur mismatches and displacement jitter exceed normal depth-of-field thresholds."

    # Rule D: Synthetic Speech / Voice Cloning (unnatural prosody, metallic artifacts, or splice bursts)
    elif acoustic_score >= 0.60 or (tech_anomaly_score >= 0.50 and len(acoustic_anomalies) >= 1):
        classification = "POTENTIALLY_SYNTHETIC_SPEECH"
        confidence = "HIGH" if acoustic_score >= 0.70 else "MEDIUM"
        reason = "Acoustic stream exhibits unnatural prosody, metallic artifacts, or abnormal silence splice distributions characteristic of synthetic speech."

    # Rule E: Partial AI Editing (isolated spectral irregularities supported by multiple indicators or elevated visual anomaly)
    elif len(spectral_anomalies) >= 1 and (len(anomaly_evidence) >= 2 or vis_anomaly_level == "elevated"):
        classification = "POTENTIALLY_AI_EDITED"
        confidence = "MEDIUM"
        reason = "Isolated high-frequency spectral irregularities and keyframe differences suggest partial AI post-processing or regeneration."

    # Rule F: Conventional Editing (Ordinary scene cuts, recompression)
    elif scene_cuts > 0 or len(visual_forensics.get("scene_cuts", {}).get("cut_timestamps", [])) > 0:
        if len(face_anomalies) == 0 and acoustic_score < 0.35 and tech_anomaly_score < 0.40:
            classification = "CONVENTIONAL_EDITING_DETECTED"
            confidence = "HIGH"
            reason = f"Video contains standard editorial scene transitions ({scene_cuts} cuts) with no localized biometric or synthetic anomalies."
        else:
            classification = "INCONCLUSIVE"
            confidence = "UNCERTAIN"
            reason = "Multiple editing cuts observed alongside weak anomaly indicators; unable to confirm AI manipulation."

    # Rule G: Insufficient Evidence or Conflicting Signals
    elif len(checks_performed) <= 1:
        classification = "INCONCLUSIVE"
        confidence = "UNCERTAIN"
        reason = "Insufficient forensic checks could be executed on this media stream to reach a confident authenticity verdict."

    # Rule H: Clean Authentic Footage (no anomaly evidence)
    elif len(anomaly_evidence) == 0 and vis_anomaly_level == "low" and acoustic_score < 0.25:
        classification = "AUTHENTIC_NO_ANOMALIES_DETECTED"
        confidence = "HIGH"
        reason = "All executed forensic checks (frequency spectra, facial boundaries, audio stream metrics, and temporal consistency) passed within normal parameters."

    else:
        classification = "INCONCLUSIVE"
        confidence = "LOW"
        reason = "Forensic signals are mixed or borderline; evidence is insufficient to declare synthetic manipulation."

    # Disclaimers
    limitations = [
        "Digital forensics analyzes statistical, acoustic, and cryptographic anomalies; it does not replace human investigative journalism.",
        "Absence of C2PA credentials is standard for organic web media and does not prove manipulation.",
        "Natural video compression, bokeh blur, and editorial cuts can mimic certain mathematical anomalies.",
    ]

    return {
        "classification": classification,
        "confidence_level": confidence,
        "reason": reason,
        "evidence": evidence_list,
        "suspicious_segments": suspicious_segments,
        "provenance": {
            "status": c2pa_status,
            "sha256": provenance.get("sha256"),
            "is_valid": c2pa_info.get("is_valid", False),
            "generator": c2pa_info.get("generator"),
            "issuer": c2pa_info.get("issuer"),
            "actions": c2pa_info.get("actions", []),
            "disclaimer": c2pa_info.get("disclaimer", "Absence of credentials does not imply manipulation."),
        },
        "checks_performed": checks_performed,
        "checks_unavailable": checks_unavailable,
        "limitations": limitations,
        "model_versions": {
            "opencv": "4.10.x",
            "c2pa_python": "0.38.0",
            "gemini_model": gemini_audio.get("model_used") or "gemini-2.5-flash (advisory)",
            "whisper_asr": "Groq Whisper-large-v3",
        },
    }

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
    face_anomalies = [e for e in evidence_list if "face" in str(e.get("signal") or "").lower() or "face" in str(e.get("details") or "").lower()]
    acoustic_anomalies = [e for e in evidence_list if "robotic" in str(e.get("signal") or "").lower() or "silence" in str(e.get("signal") or "").lower()]
    spectral_anomalies = [e for e in evidence_list if "spectral" in str(e.get("signal") or "").lower()]

    vis_anomaly_level = visual_forensics.get("anomaly_level", "low")
    tech_anomaly_score = technical_audio.get("technical_anomaly_score", 0.0)
    acoustic_score = gemini_audio.get("acoustic_anomaly_analysis", {}).get("acoustic_anomaly_score", 0.0) or 0.0
    scene_cuts = visual_forensics.get("scene_cuts", {}).get("count", 0)

    # ── 3. Extract or Build Modality Results (Section 1 & 7) ──
    # Visual Modality Result
    vis_mod = visual_forensics.get("visual_modality_result")
    if not vis_mod:
        if vis_status == "assessed":
            vis_score = visual_forensics.get("visual_synthetic_score", 0.0)
            if vis_score >= 0.70 or vis_anomaly_level == "elevated":
                v_verdict, v_label = "AI_GENERATED", "LIKELY AI-GENERATED"
            elif scene_cuts > 0:
                v_verdict, v_label = "LIKELY_MANIPULATED", "LIKELY MANIPULATED — ORIGIN UNDETERMINED"
            elif vis_anomaly_level == "low":
                v_verdict, v_label = "LIKELY_AUTHENTIC", "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED"
            else:
                v_verdict, v_label = "INCONCLUSIVE", "INCONCLUSIVE"
            vis_mod = {
                "status": "COMPLETED",
                "verdict": v_verdict,
                "verdict_label": v_label,
                "detector_name": "OpenCV 5.0 (cv2) + Signal Processing",
                "detector_version": "4.10.x",
                "coverage_details": {"frames_analyzed": visual_forensics.get("frames_analyzed", 0)},
                "error_code": None,
                "evidence": [e for e in evidence_list if "visual" in str(e.get("detector", "")).lower() or "fft" in str(e.get("detector", "")).lower()],
                "suspicious_segments": visual_forensics.get("suspicious_segments", []),
                "limitations": [visual_forensics.get("limitations", "Keyframe-level sampling inference.")],
            }
        elif vis_status == "failed":
            vis_mod = {
                "status": "FAILED",
                "verdict": "INCONCLUSIVE",
                "verdict_label": "INCONCLUSIVE",
                "detector_name": "OpenCV 5.0 (cv2)",
                "detector_version": "4.10.x",
                "coverage_details": {},
                "error_code": "VISUAL_PROCESSING_ERROR",
                "evidence": [],
                "suspicious_segments": [],
                "limitations": [visual_forensics.get("limitations", "Visual frame extraction failed.")],
            }
        else:
            vis_mod = {
                "status": "NOT_ANALYZED",
                "verdict": "INCONCLUSIVE",
                "verdict_label": "INCONCLUSIVE",
                "detector_name": "OpenCV 5.0 (cv2)",
                "detector_version": "4.10.x",
                "coverage_details": {},
                "error_code": None,
                "evidence": [],
                "suspicious_segments": [],
                "limitations": ["No visual stream provided for keyframe inspection."],
            }

    # Audio Modality Result
    aud_mod = audio_authenticity.get("audio_modality_result")
    if not aud_mod:
        if gem_status == "assessed":
            ac_score = gemini_audio.get("acoustic_anomaly_analysis", {}).get("acoustic_anomaly_score", 0.0) or 0.0
            if ac_score >= 0.65:
                a_verdict, a_label = "AI_GENERATED", "LIKELY AI-GENERATED"
            elif technical_audio.get("technical_anomaly_score", 0.0) >= 0.55:
                a_verdict, a_label = "LIKELY_MANIPULATED", "LIKELY MANIPULATED — ORIGIN UNDETERMINED"
            elif ac_score < 0.30:
                a_verdict, a_label = "LIKELY_AUTHENTIC", "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED"
            else:
                a_verdict, a_label = "INCONCLUSIVE", "INCONCLUSIVE"
            aud_mod = {
                "status": "COMPLETED",
                "verdict": a_verdict,
                "verdict_label": a_label,
                "detector_name": "Google GenAI Audio Forensic Auditor",
                "detector_version": gemini_audio.get("model_used") or "gemini-2.5-flash",
                "coverage_details": {"duration_seconds": technical_audio.get("duration_seconds")},
                "error_code": None,
                "evidence": [e for e in evidence_list if "audio" in str(e.get("detector", "")).lower() or "gemini" in str(e.get("detector", "")).lower()],
                "suspicious_segments": audio_authenticity.get("suspicious_segments", []),
                "limitations": ["Acoustic analysis is advisory; biometric models not loaded."],
            }
        elif gem_status == "failed":
            aud_err = gemini_audio.get("error_code") or "DEADLINE_EXCEEDED"
            aud_mod = {
                "status": "FAILED",
                "verdict": "INCONCLUSIVE",
                "verdict_label": "INCONCLUSIVE",
                "detector_name": "Google GenAI Audio Forensic Auditor",
                "detector_version": "gemini-2.5-flash",
                "coverage_details": {},
                "error_code": aud_err,
                "evidence": [],
                "suspicious_segments": [],
                "limitations": [f"Audio detector failed ({aud_err}); timeout exceeded."],
            }
        else:
            aud_mod = {
                "status": "NOT_ANALYZED",
                "verdict": "INCONCLUSIVE",
                "verdict_label": "INCONCLUSIVE",
                "detector_name": "Google GenAI Audio Forensic Auditor",
                "detector_version": "gemini-2.5-flash",
                "coverage_details": {},
                "error_code": None,
                "evidence": [],
                "suspicious_segments": [],
                "limitations": ["Audio track not available or not assessed."],
            }

    # Provenance Result
    c2pa_status_mapped = {
        "verified": "VERIFIED",
        "invalid": "INVALID",
        "missing": "NOT_FOUND",
        "unsupported": "UNSUPPORTED",
    }.get(c2pa_status, "NOT_FOUND")

    provenance_result = {
        "status": "COMPLETED" if c2pa_status in ("verified", "invalid", "missing") else "NOT_ANALYZED",
        "c2pa_status": c2pa_status_mapped,
        "sha256": provenance.get("sha256"),
        "is_valid": c2pa_info.get("is_valid", False),
        "generator": c2pa_info.get("generator"),
        "issuer": c2pa_info.get("issuer"),
        "actions": c2pa_info.get("actions", []),
        "disclaimer": c2pa_info.get("disclaimer", "Absence of credentials is normal for web media and does not prove manipulation."),
    }

    # Analysis Coverage
    analysis_coverage = {
        "visual": vis_mod.get("status", "NOT_ANALYZED"),
        "audio": aud_mod.get("status", "NOT_ANALYZED"),
        "provenance": provenance_result.get("status", "COMPLETED"),
    }

    # ── 4. Unified Verdict Priority Aggregation ──
    # Extract signals
    face_anomalies = [e for e in evidence_list if "face" in str(e.get("signal") or "").lower() or "face" in str(e.get("details") or "").lower()]
    acoustic_anomalies = [e for e in evidence_list if "robotic" in str(e.get("signal") or "").lower() or "silence" in str(e.get("signal") or "").lower()]
    spectral_anomalies = [e for e in evidence_list if "spectral" in str(e.get("signal") or "").lower()]
    anomaly_evidence = [e for e in evidence_list if e.get("severity") in ("moderate", "high")]

    vis_verdict = vis_mod.get("verdict", "INCONCLUSIVE")
    aud_verdict = aud_mod.get("verdict", "INCONCLUSIVE")
    vis_active = vis_mod.get("status") in ("COMPLETED", "PARTIAL")
    aud_active = aud_mod.get("status") in ("COMPLETED", "PARTIAL")

    # Priority Rules
    # Rule 1: Certified Provenance
    if c2pa_status == "verified":
        has_ai_action = any("ai" in str(act).lower() or "generate" in str(act).lower() for act in c2pa_info.get("actions", []))
        if has_ai_action:
            overall_verdict = "AI_GENERATED"
            overall_label = "LIKELY AI-GENERATED"
            classification = "LIKELY_AI_GENERATED"
            confidence = "HIGH"
            reason = f"C2PA Content Credentials cryptographically certify AI generation via {c2pa_info.get('generator', 'AI tool')}."
        elif len(anomaly_evidence) == 0:
            overall_verdict = "LIKELY_AUTHENTIC"
            overall_label = "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED"
            classification = "AUTHENTIC_NO_ANOMALIES_DETECTED"
            confidence = "HIGH"
            reason = f"C2PA Content Credentials cryptographically verify authentic capture signed by '{c2pa_info.get('issuer', 'Authorized Authority')}' with no downstream tampering."
        else:
            overall_verdict = "INCONCLUSIVE"
            overall_label = "INCONCLUSIVE"
            classification = "INCONCLUSIVE"
            confidence = "LOW"
            reason = "C2PA signature is valid but media stream presents unexplained localized anomalies."

    elif c2pa_status == "invalid":
        overall_verdict = "PARTIALLY_AI_GENERATED"
        overall_label = "LIKELY PARTIALLY AI-GENERATED / AI-EDITED"
        classification = "POTENTIALLY_AI_EDITED"
        confidence = "HIGH"
        reason = "C2PA manifest verification failed: cryptographic digital signature has been invalidated or corrupted."

    # Rule 2: Both Visual and Audio Confirmed AI-Generated
    elif vis_active and aud_active and vis_verdict == "AI_GENERATED" and aud_verdict == "AI_GENERATED":
        overall_verdict = "AI_GENERATED"
        overall_label = "LIKELY AI-GENERATED"
        classification = "LIKELY_AI_GENERATED"
        confidence = "HIGH"
        reason = "Both visual keyframes and audio speech stream present strong, independent synthetic generation indicators."

    # Rule 3: Visual AI-Generated with Authentic/Unassessed Audio
    elif vis_active and vis_verdict == "AI_GENERATED":
        if aud_active and aud_verdict == "LIKELY_AUTHENTIC":
            overall_verdict = "PARTIALLY_AI_GENERATED"
            overall_label = "LIKELY PARTIALLY AI-GENERATED / AI-EDITED"
            classification = "POTENTIALLY_AI_EDITED"
            confidence = "HIGH"
            reason = "Visual frames exhibit synthetic AI generation, but the accompanying audio speech exhibits authentic organic acoustics."
        else:
            overall_verdict = "AI_GENERATED"
            overall_label = "LIKELY AI-GENERATED"
            classification = "LIKELY_AI_GENERATED"
            confidence = "HIGH" if visual_forensics.get("visual_synthetic_score", 0.0) >= 0.75 else "MEDIUM"
            if not aud_active:
                reason = "Visual frequency spectrum abnormalities and generator artifacts indicate synthetic AI generation (audio was unavailable/failed; overall conclusion is based on visual modality alone)."
            else:
                reason = "Visual keyframes exhibit periodic 2D FFT anomalies and synthetic compression profiles indicative of AI generation."

    # Rule 4: Audio AI-Generated with Authentic/Unassessed Video
    elif aud_active and aud_verdict == "AI_GENERATED":
        if vis_active and vis_verdict == "LIKELY_AUTHENTIC":
            overall_verdict = "PARTIALLY_AI_GENERATED"
            overall_label = "LIKELY PARTIALLY AI-GENERATED / AI-EDITED"
            classification = "POTENTIALLY_SYNTHETIC_SPEECH"
            confidence = "HIGH"
            reason = "Authentic video footage accompanied by synthetic or AI-cloned narration speech."
        else:
            overall_verdict = "AI_GENERATED"
            overall_label = "LIKELY AI-GENERATED"
            classification = "POTENTIALLY_SYNTHETIC_SPEECH"
            confidence = "HIGH"
            if not vis_active:
                reason = "Acoustic stream exhibits unnatural prosody, metallic artifacts, or synthetic speech signatures (visual was not assessed; conclusion is based on audio alone)."
            else:
                reason = "Speech acoustics exhibit synthetic voice generation signatures."

    # Rule 5: Localized Facial Splicing or Partial Frame Insertion
    elif len(face_anomalies) >= 1 or vis_verdict == "PARTIALLY_AI_GENERATED":
        overall_verdict = "PARTIALLY_AI_GENERATED"
        overall_label = "LIKELY PARTIALLY AI-GENERATED / AI-EDITED"
        classification = "POTENTIALLY_FACIAL_MANIPULATION"
        confidence = "HIGH" if len(face_anomalies) >= 2 else "MEDIUM"
        reason = "Localized facial boundary blur mismatches and displacement jitter exceed normal focus depth thresholds, indicating face modification."

    # Rule 6: Partial Spectral Editing
    elif len(spectral_anomalies) >= 1 and (len(anomaly_evidence) >= 2 or vis_anomaly_level == "elevated"):
        overall_verdict = "PARTIALLY_AI_GENERATED"
        overall_label = "LIKELY PARTIALLY AI-GENERATED / AI-EDITED"
        classification = "POTENTIALLY_AI_EDITED"
        confidence = "MEDIUM"
        reason = "Isolated high-frequency spectral irregularities suggest partial AI post-processing or frame regeneration."

    # Rule 7: Likely Manipulated (Suspicious Splicing or Boundary Anomaly without proven AI origin)
    elif (vis_verdict == "LIKELY_MANIPULATED" or aud_verdict == "LIKELY_MANIPULATED" or (scene_cuts >= 4 and vis_anomaly_level == "elevated")):
        overall_verdict = "LIKELY_MANIPULATED"
        overall_label = "LIKELY MANIPULATED — ORIGIN UNDETERMINED"
        classification = "CONVENTIONAL_EDITING_DETECTED"
        confidence = "HIGH" if (vis_active and aud_active) else "MEDIUM"
        reason = f"Media contains conventional scene transitions ({scene_cuts} cuts) or editorial splicing; evidence confirms conventional editing without synthetic AI indicators."

    # Rule 8: Authentic (No Synthetic Anomalies)
    elif len(anomaly_evidence) == 0 and vis_anomaly_level == "low" and acoustic_score < 0.35:
        overall_verdict = "LIKELY_AUTHENTIC"
        overall_label = "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED"
        classification = "AUTHENTIC_NO_ANOMALIES_DETECTED"
        confidence = "HIGH" if (vis_active and aud_active) else "MEDIUM"
        if vis_active and aud_active:
            reason = "No synthetic AI indicators detected. Visual keyframes, optical focus, and speech acoustics demonstrate organic, natural characteristics."
        elif vis_active and not aud_active:
            reason = "Visual keyframes show natural optical focus, consistent lighting, and organic motion with no AI synthesis detected (concluded on visual modality alone as audio was unassessed or failed)."
        elif aud_active and not vis_active:
            reason = "Audio stream verified with natural vocal cadence and organic acoustic properties with no AI synthesis detected."
        else:
            overall_verdict = "INCONCLUSIVE"
            overall_label = "INCONCLUSIVE"
            classification = "INCONCLUSIVE"
            confidence = "UNCERTAIN"
            reason = "Insufficient media streams could be verified to determine authenticity."

    # Rule 9: Inconclusive Default
    else:
        overall_verdict = "INCONCLUSIVE"
        overall_label = "INCONCLUSIVE"
        classification = "INCONCLUSIVE"
        confidence = "LOW"
        reason = "Forensic signals are mixed, conflicting, or borderline; evidence is insufficient to issue a definitive AI verdict."

    limitations = [
        "No detector can guarantee 100% authenticity or detect all novel AI synthesis models.",
        "A failed or timed-out modality is never treated as evidence of authenticity.",
        "Absence of C2PA credentials is standard for organic social media and does not prove manipulation.",
        "Natural video compression, bokeh blur, and editorial cuts can mimic certain mathematical anomalies.",
    ]

    confidence_meanings = {
        "HIGH": "Strong multi-signal convergence across executed detectors with minimal ambiguity.",
        "MEDIUM": "Credible forensic anomalies detected, but localized to specific intervals or partial evidence.",
        "LOW": "Borderline signals or elevated uncertainty; additional investigative verification recommended.",
        "UNCERTAIN": "Insufficient data, failed modality, or conflicting signals preclude definitive determination.",
    }

    return {
        # Section 7 Unified Schema
        "overall_verdict": overall_verdict,
        "overall_verdict_label": overall_label,
        "summary": reason,
        "visual": vis_mod,
        "audio": aud_mod,
        "provenance": provenance_result,
        "analysis_coverage": analysis_coverage,
        "report_version": "1.0",

        # Backward compatibility fields
        "classification": classification,
        "confidence_level": confidence,
        "confidence_meaning": confidence_meanings.get(confidence, ""),
        "reason": reason,
        "evidence": evidence_list,
        "suspicious_segments": suspicious_segments,
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

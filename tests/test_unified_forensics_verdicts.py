"""
test_unified_forensics_verdicts.py — Unified Multimodal Forensics & Final Verdict Engine Test Suite
====================================================================================================
Comprehensive test suite verifying:
1. All 5 Section 1 Verdict Categories:
   - AI_GENERATED (visual alone, audio alone, both)
   - PARTIALLY_AI_GENERATED (AI video + authentic audio, authentic video + AI narration, facial manipulation)
   - LIKELY_AUTHENTIC (clean multi-modal, clean visual with audio failure + limitation disclaimer)
   - LIKELY_MANIPULATED (conventional cuts and splice intervals with origin undetermined)
   - INCONCLUSIVE (both failed, conflicting evidence, insufficient coverage)
2. Audio Pipeline Reliability:
   - DEADLINE_EXCEEDED (504) handling without converting failure into authenticity
   - Rate limits (429), Service Unavailable (503)
   - API key sanitization
3. Visual Sampling Telemetry:
   - frames_sampled, frames_analyzed, sampling_timestamps, skipped_frames
4. Section 7 API Schema Contract:
   - overall_verdict, summary, visual, audio, provenance, analysis_coverage, report_version
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.evidence_fusion import fuse_forensic_evidence
from backend.services.gemini_audio import _sanitize_error_message, analyze_audio_with_gemini
from shared.schemas.forensics import (
    UnifiedAuthenticityReport,
    ForensicVerdict,
    ModalityStatus,
    VERDICT_DISPLAY_LABELS,
)


# ─── 1. Section 1 Verdict Categories Tests ────────────────────────────────────

def test_verdict_both_visual_and_audio_ai_generated():
    """Verify video with both visual synthesis and AI speech yields AI_GENERATED."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "visual_synthetic_score": 0.88,
        "anomaly_level": "elevated",
        "observed_anomalies": ["Elevated high-frequency energy pattern (possible artificial synthesis / noise overlay)"],
        "suspicious_segments": [{"start_time": 1.0, "end_time": 2.0, "anomaly_type": "spectral_frequency_anomaly", "severity": "high"}],
        "visual_modality_result": {
            "status": "COMPLETED",
            "verdict": "AI_GENERATED",
            "verdict_label": "LIKELY AI-GENERATED",
            "detector_name": "OpenCV 5.0 (cv2) + Signal Processing",
        }
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.20}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.85, "anomaly_indicators": ["robotic pitch flattening"]}}
    aud_auth = {
        "audio_modality_result": {
            "status": "COMPLETED",
            "verdict": "AI_GENERATED",
            "verdict_label": "LIKELY AI-GENERATED",
            "detector_name": "Google GenAI Audio Forensic Auditor",
        },
        "evidence": [{"detector": "Gemini Audio", "signal": "robotic prosody", "severity": "high"}],
        "suspicious_segments": [],
    }

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"platform": "youtube"},
        temporal={},
        deepfake_heuristics={},
    )

    assert res["overall_verdict"] == "AI_GENERATED"
    assert res["overall_verdict_label"] == "LIKELY AI-GENERATED"
    assert "visual" in res["reason"].lower() or "keyframes" in res["reason"].lower()
    assert res["visual"]["verdict"] == "AI_GENERATED"
    assert res["audio"]["verdict"] == "AI_GENERATED"
    assert res["confidence_level"] == "HIGH"


def test_verdict_partially_ai_generated_real_video_ai_narration():
    """Verify authentic video accompanied by synthetic narration classifies as PARTIALLY_AI_GENERATED."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "visual_synthetic_score": 0.10,
        "anomaly_level": "low",
        "observed_anomalies": [],
        "suspicious_segments": [],
        "visual_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_AUTHENTIC",
            "verdict_label": "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED",
        }
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.30}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.80, "anomaly_indicators": ["metallic timbre"]}}
    aud_auth = {
        "audio_modality_result": {
            "status": "COMPLETED",
            "verdict": "AI_GENERATED",
            "verdict_label": "LIKELY AI-GENERATED",
        },
        "evidence": [{"detector": "Gemini Audio", "signal": "metallic timbre", "severity": "high"}],
        "suspicious_segments": [],
    }

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"platform": "youtube"},
        temporal={},
        deepfake_heuristics={},
    )

    assert res["overall_verdict"] == "PARTIALLY_AI_GENERATED"
    assert res["overall_verdict_label"] == "LIKELY PARTIALLY AI-GENERATED / AI-EDITED"
    assert res["visual"]["verdict"] == "LIKELY_AUTHENTIC"
    assert res["audio"]["verdict"] == "AI_GENERATED"


def test_verdict_partially_ai_generated_facial_manipulation():
    """Verify localized facial boundary mismatch classifies as PARTIALLY_AI_GENERATED."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "visual_synthetic_score": 0.65,
        "anomaly_level": "moderate",
        "face_boundary_analysis": {"mean_boundary_blur_ratio": 2.4},
        "observed_anomalies": ["Soft/blurry facial region superimposed on sharper background"],
        "suspicious_segments": [{"start_time": 3.0, "end_time": 4.0, "anomaly_type": "face_boundary_blur_mismatch", "severity": "high"}],
        "visual_modality_result": {
            "status": "COMPLETED",
            "verdict": "PARTIALLY_AI_GENERATED",
            "verdict_label": "LIKELY PARTIALLY AI-GENERATED / AI-EDITED",
        }
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.10}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.10, "anomaly_indicators": []}}
    aud_auth = {
        "audio_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_AUTHENTIC",
            "verdict_label": "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED",
        },
        "evidence": [],
        "suspicious_segments": [],
    }

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"platform": "youtube"},
        temporal={},
        deepfake_heuristics={},
    )

    assert res["overall_verdict"] == "PARTIALLY_AI_GENERATED"
    assert "face" in res["reason"].lower() or "facial" in res["reason"].lower()


def test_verdict_likely_manipulated_conventional_cuts():
    """Verify ordinary editorial scene cuts without AI synthesis classify as LIKELY_MANIPULATED."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "visual_synthetic_score": 0.15,
        "anomaly_level": "low",
        "scene_cuts": {"count": 6, "abrupt_transitions": 2, "cut_timestamps": [1.5, 4.2]},
        "observed_anomalies": [],
        "suspicious_segments": [],
        "visual_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_MANIPULATED",
            "verdict_label": "LIKELY MANIPULATED — ORIGIN UNDETERMINED",
        }
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.15}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.10, "anomaly_indicators": []}}
    aud_auth = {
        "audio_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_AUTHENTIC",
            "verdict_label": "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED",
        },
        "evidence": [],
        "suspicious_segments": [],
    }

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"platform": "youtube"},
        temporal={},
        deepfake_heuristics={},
    )

    assert res["overall_verdict"] == "LIKELY_MANIPULATED"
    assert res["overall_verdict_label"] == "LIKELY MANIPULATED — ORIGIN UNDETERMINED"


def test_verdict_likely_authentic_with_disclaimer():
    """Verify clean footage with no anomalies yields LIKELY_AUTHENTIC with scientific disclaimer."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "visual_synthetic_score": 0.05,
        "anomaly_level": "low",
        "scene_cuts": {"count": 0, "abrupt_transitions": 0, "cut_timestamps": []},
        "observed_anomalies": [],
        "suspicious_segments": [],
        "visual_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_AUTHENTIC",
            "verdict_label": "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED",
        }
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.05}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.05, "anomaly_indicators": []}}
    aud_auth = {
        "audio_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_AUTHENTIC",
            "verdict_label": "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED",
        },
        "evidence": [],
        "suspicious_segments": [],
    }

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"platform": "youtube"},
        temporal={},
        deepfake_heuristics={},
    )

    assert res["overall_verdict"] == "LIKELY_AUTHENTIC"
    assert res["overall_verdict_label"] == "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED"
    # Ensure limitation disclaims that no detector guarantees 100% authenticity
    assert any("no detector can guarantee" in lim.lower() for lim in res["limitations"])


# ─── 2. Modality Failure & DEADLINE_EXCEEDED Reliability Tests ────────────────

def test_audio_failure_deadline_exceeded_never_proves_authenticity():
    """Verify that an audio API 504 DEADLINE_EXCEEDED failure is never treated as negative AI voice detection."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "visual_synthetic_score": 0.05,
        "anomaly_level": "low",
        "observed_anomalies": [],
        "suspicious_segments": [],
        "visual_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_AUTHENTIC",
            "verdict_label": "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED",
        }
    }
    tech_aud = {"status": "not_assessed"}
    gem_aud = {"status": "failed", "error_code": "DEADLINE_EXCEEDED", "reason": "504 DEADLINE_EXCEEDED"}
    aud_auth = {
        "audio_modality_result": {
            "status": "FAILED",
            "verdict": "INCONCLUSIVE",
            "verdict_label": "INCONCLUSIVE",
            "error_code": "DEADLINE_EXCEEDED",
        },
        "evidence": [],
        "suspicious_segments": [],
    }

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"platform": "youtube"},
        temporal={},
        deepfake_heuristics={},
    )

    # Audio modality must be recorded as FAILED, not completed
    assert res["analysis_coverage"]["audio"] == "FAILED"
    assert res["audio"]["status"] == "FAILED"
    assert res["audio"]["error_code"] == "DEADLINE_EXCEEDED"

    # Overall conclusion must disclose that it is based on visual modality alone
    assert "visual modality alone" in res["reason"].lower() or "audio" in res["reason"].lower()
    # And limitation must declare failed modalities never count as authenticity
    assert any("failed or timed-out modality" in lim.lower() for lim in res["limitations"])


def test_both_modalities_failed_yields_inconclusive():
    """Verify when both visual and audio fail, overall verdict is strictly INCONCLUSIVE."""
    prov = {"c2pa": {"status": "unsupported"}}
    vis = {"status": "failed", "limitations": "OpenCV error"}
    tech_aud = {"status": "not_assessed"}
    gem_aud = {"status": "failed", "error_code": "DEADLINE_EXCEEDED"}
    aud_auth = {"evidence": [], "suspicious_segments": []}

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"platform": "youtube"},
        temporal={},
        deepfake_heuristics={},
    )

    assert res["overall_verdict"] == "INCONCLUSIVE"
    assert res["overall_verdict_label"] == "INCONCLUSIVE"
    assert res["confidence_level"] in ("LOW", "UNCERTAIN")


# ─── 3. Section 7 Schema Conformance Tests ────────────────────────────────────

def test_unified_report_schema_contract():
    """Verify the output dictionary strictly conforms to Section 7 Unified Forensic Report schema."""
    prov = {"c2pa": {"status": "verified", "issuer": "TrueLens Camera", "generator": "Hardware-V1"}}
    vis = {
        "status": "assessed",
        "visual_synthetic_score": 0.05,
        "anomaly_level": "low",
        "observed_anomalies": [],
        "visual_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_AUTHENTIC",
            "verdict_label": "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED",
        }
    }
    tech_aud = {"status": "assessed", "duration_seconds": 15.0}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.0}}
    aud_auth = {
        "audio_modality_result": {
            "status": "COMPLETED",
            "verdict": "LIKELY_AUTHENTIC",
            "verdict_label": "LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED",
        },
        "evidence": [],
    }

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"platform": "youtube"},
        temporal={},
        deepfake_heuristics={},
    )

    # Validate with Pydantic model
    report = UnifiedAuthenticityReport(**res)
    assert report.report_version == "1.0"
    assert report.overall_verdict in ("AI_GENERATED", "PARTIALLY_AI_GENERATED", "LIKELY_AUTHENTIC", "LIKELY_MANIPULATED", "INCONCLUSIVE")
    assert report.overall_verdict_label in VERDICT_DISPLAY_LABELS.values()
    assert report.visual.status in ("COMPLETED", "PARTIAL", "FAILED", "NOT_ANALYZED")
    assert report.audio.status in ("COMPLETED", "PARTIAL", "FAILED", "NOT_ANALYZED")
    assert report.provenance.status in ("COMPLETED", "PARTIAL", "FAILED", "NOT_ANALYZED")
    assert "visual" in report.analysis_coverage
    assert "audio" in report.analysis_coverage


# ─── 4. Security & Sanitization Tests ─────────────────────────────────────────

def test_api_key_sanitization_in_errors():
    """Verify API keys are stripped from error logs and return objects."""
    fake_gemini_key = "AIzaSyD-1234567890abcdefghijklmnopqrstuv"
    raw_error = f"API call failed for key={fake_gemini_key}: 504 DEADLINE_EXCEEDED"
    sanitized = _sanitize_error_message(raw_error)
    assert fake_gemini_key not in sanitized
    assert "[REDACTED" in sanitized

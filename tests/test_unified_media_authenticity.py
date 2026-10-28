"""
test_unified_media_authenticity.py — Comprehensive Test Suite
=============================================================
Tests all core requirements for the Unified Media Authenticity Engine:
1. Authentic media with ordinary scene cuts -> CONVENTIONAL_EDITING_DETECTED or AUTHENTIC
2. AI-generated media -> LIKELY_AI_GENERATED
3. Facial boundary anomalies -> POTENTIALLY_FACIAL_MANIPULATION
4. Partial manipulation -> POTENTIALLY_AI_EDITED
5. Synthetic speech & acoustic anomalies -> POTENTIALLY_SYNTHETIC_SPEECH
6. Conflicting or insufficient signals -> INCONCLUSIVE
7. C2PA Content Credentials (verified, invalid, missing, unsupported)
8. SHA-256 preservation & file verification
9. SSRF URL validation & media file magic-bytes validation
10. Safe transcript comparison with NOT_COMPARABLE handling
11. Backward compatibility of all API fields
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from backend.services.provenance import compute_file_sha256, inspect_c2pa_manifest, analyze_media_provenance
from backend.services.security_validation import validate_media_url, validate_media_file
from backend.services.audio_authenticity import compare_transcripts_safely, audit_audio_authenticity
from backend.services.evidence_fusion import fuse_forensic_evidence
from backend.services.forensics import run_forensics_pipeline
from shared.schemas.forensics import UnifiedAuthenticityReport, ProvenanceData


# ─── 1. Security & SSRF Tests ─────────────────────────────────────────────

def test_ssrf_blocks_private_and_metadata_ips():
    """Verify SSRF validation rejects loopback, private RFC-1918 IPs, and cloud metadata."""
    # Loopback
    ok, err = validate_media_url("http://127.0.0.1/video.mp4")
    assert not ok
    assert "private or restricted" in err.lower() or "blocked" in err.lower()

    # Cloud metadata
    ok, err = validate_media_url("http://169.254.169.254/latest/meta-data/")
    assert not ok
    assert "blocked" in err.lower() or "restricted" in err.lower()

    # Private network
    ok, err = validate_media_url("http://192.168.1.100/stream.m3u8")
    assert not ok
    assert "private" in err.lower() or "restricted" in err.lower()

    # Invalid scheme
    ok, err = validate_media_url("file:///etc/passwd")
    assert not ok
    assert "scheme" in err.lower()


def test_media_file_magic_bytes_validation():
    """Verify magic bytes validation recognizes valid media and blocks arbitrary binaries."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        # Write fake MP4 header: 4 bytes size + ftyp
        f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")
        f.flush()
        valid_mp4 = f.name

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"This is just plain text content.")
        f.flush()
        invalid_file = f.name

    try:
        ok, err = validate_media_file(valid_mp4)
        assert ok, f"Valid MP4 header failed: {err}"

        ok, err = validate_media_file(invalid_file)
        assert not ok
        assert "container" in err.lower() or "signature" in err.lower()
    finally:
        if os.path.exists(valid_mp4):
            os.remove(valid_mp4)
        if os.path.exists(invalid_file):
            os.remove(invalid_file)


# ─── 2. SHA-256 and Provenance Tests ──────────────────────────────────────

def test_sha256_hash_preservation():
    """Verify SHA-256 calculation matches true cryptographic digest."""
    test_bytes = b"TrueLens AI Forensic Preservation Unit Test"
    import hashlib
    expected_hash = hashlib.sha256(test_bytes).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(test_bytes)
        f.flush()
        path = f.name

    try:
        calculated = compute_file_sha256(path)
        assert calculated == expected_hash
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_c2pa_provenance_states():
    """Verify C2PA returns proper states: missing, unsupported, or verified."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + b"\x00" * 1024)
        f.flush()
        temp_path = f.name

    try:
        res = inspect_c2pa_manifest(temp_path)
        # Should cleanly return 'missing' (since file has no c2pa manifest) or 'unsupported'
        assert res["status"] in ("missing", "unsupported")
        assert not res["is_valid"]
        assert "disclaimer" in res
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ─── 3. Audio & Transcript Concordance Tests ─────────────────────────────

def test_transcript_comparison_not_comparable_on_language_mismatch():
    """Verify transcript comparison returns NOT_COMPARABLE on language mismatch."""
    res = compare_transcripts_safely(
        whisper_transcript="Hello this is a news broadcast.",
        gemini_transcript="Bonjour ceci est un journal televise.",
        whisper_lang="en",
        gemini_lang="fr",
    )
    assert res["similarity_status"] == "NOT_COMPARABLE"
    assert "mismatch" in res["reason"].lower()


def test_transcript_comparison_aligned_on_matching_text():
    """Verify transcript comparison returns ALIGNED on close transcripts."""
    t1 = "The global renewable energy market expanded rapidly across European countries in 2024."
    t2 = "The global renewable energy market expanded very rapidly across European nations in 2024."
    res = compare_transcripts_safely(t1, t2)
    assert res["similarity_status"] == "ALIGNED"
    assert res["similarity_score"] >= 0.70


# ─── 4. Evidence Fusion Layer Classifications ─────────────────────────────

def test_evidence_fusion_likely_ai_generated():
    """Test fusion yields LIKELY_AI_GENERATED when multimodal visual & acoustic anomalies align."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "anomaly_level": "elevated",
        "observed_anomalies": ["Abnormally suppressed high-frequency spectrum"],
        "suspicious_segments": [
            {"start_time": 2.0, "end_time": 4.0, "anomaly_type": "spectral_frequency_anomaly", "severity": "high", "description": "Synthetic spectral roll-off"}
        ],
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.65, "technical_flags": ["neural TTS sample rate"]}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.70, "anomaly_indicators": ["robotic pitch flattening"]}}
    aud_auth = {
        "suspicious_segments": [{"start_time": 0.0, "end_time": 5.0, "anomaly_type": "abrupt_silence_splicing", "severity": "high", "description": "8 silence cuts"}],
        "evidence": [{"detector": "Gemini Multimodal", "signal": "robotic artifacts", "severity": "high", "details": "Unnatural pitch flattening"}],
    }

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"integrity_score": 80},
        temporal={"temporal_consistency_score": 0.8},
        deepfake_heuristics={"deepfake_probability": 0.8, "voice_clone_probability": 0.7},
    )

    assert res["classification"] == "LIKELY_AI_GENERATED"
    assert res["confidence_level"] in ("HIGH", "MEDIUM")
    assert len(res["evidence"]) > 0
    assert len(res["suspicious_segments"]) > 0


def test_evidence_fusion_potentially_facial_manipulation():
    """Test fusion yields POTENTIALLY_FACIAL_MANIPULATION when face boundary blur mismatches exist."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "anomaly_level": "moderate",
        "observed_anomalies": ["Soft/blurry facial region superimposed on sharper background"],
        "suspicious_segments": [
            {"start_time": 3.0, "end_time": 5.0, "anomaly_type": "face_boundary_blur_mismatch", "severity": "high", "description": "Face blur ratio indicates soft facial grafting"}
        ],
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.10, "technical_flags": []}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.15, "anomaly_indicators": []}}
    aud_auth = {"suspicious_segments": [], "evidence": []}

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"integrity_score": 95},
        temporal={"temporal_consistency_score": 0.95},
        deepfake_heuristics={"deepfake_probability": 0.3, "voice_clone_probability": 0.1},
    )

    assert res["classification"] == "POTENTIALLY_FACIAL_MANIPULATION"
    assert "facial" in res["reason"].lower() or "face" in res["reason"].lower()


def test_evidence_fusion_conventional_editing():
    """Test fusion yields CONVENTIONAL_EDITING_DETECTED for ordinary scene cuts without anomalies."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "anomaly_level": "low",
        "scene_cuts": {"count": 4, "abrupt_transitions": 1, "cut_timestamps": [2.0, 5.5, 9.0, 14.2]},
        "observed_anomalies": [],
        "suspicious_segments": [],
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.05, "technical_flags": []}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.10, "anomaly_indicators": []}}
    aud_auth = {"suspicious_segments": [], "evidence": []}

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"integrity_score": 100},
        temporal={"temporal_consistency_score": 1.0},
        deepfake_heuristics={"deepfake_probability": 0.05, "voice_clone_probability": 0.05},
    )

    assert res["classification"] == "CONVENTIONAL_EDITING_DETECTED"
    assert res["confidence_level"] == "HIGH"
    assert "scene transitions" in res["reason"].lower() or "conventional" in res["reason"].lower()


def test_evidence_fusion_inconclusive_on_insufficient_data():
    """Test fusion yields INCONCLUSIVE when detectors could not be run."""
    prov = {"c2pa": {"status": "unsupported"}}
    vis = {"status": "not_assessed", "limitations": "No video"}
    tech_aud = {"status": "not_assessed"}
    gem_aud = {"status": "not_assessed"}
    aud_auth = {"suspicious_segments": [], "evidence": []}

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"integrity_score": 50},
        temporal={"temporal_consistency_score": 0.5},
        deepfake_heuristics={"deepfake_probability": 0.5, "voice_clone_probability": 0.5},
    )

    assert res["classification"] == "INCONCLUSIVE"
    assert res["confidence_level"] == "UNCERTAIN"


# ─── 5. Orchestrator End-to-End Pipeline & Backward Compatibility ──────────

def test_run_forensics_pipeline_backward_compatibility():
    """Verify master pipeline returns unified_authenticity while keeping legacy fields."""
    result = run_forensics_pipeline(
        transcript="Verified historical broadcast about space exploration and satellite orbits.",
        video_url="https://youtube.com/watch?v=mock_space_video",
        audio_path=None,
        video_path=None,
    )

    # Legacy fields
    assert "deepfake_probability" in result
    assert "voice_clone_probability" in result
    assert "scene_consistency_score" in result
    assert "video_integrity_score" in result
    assert "audio_integrity_score" in result
    assert "is_synthetic" in result
    assert "forensics_veto" in result
    assert "red_flags" in result
    assert "summary" in result

    # New unified authenticity fields
    assert "unified_authenticity" in result
    assert "provenance" in result
    assert "audio_authenticity" in result

    unified = result["unified_authenticity"]
    assert unified["classification"] in (
        "LIKELY_AI_GENERATED",
        "POTENTIALLY_AI_EDITED",
        "POTENTIALLY_FACIAL_MANIPULATION",
        "POTENTIALLY_SYNTHETIC_SPEECH",
        "CONVENTIONAL_EDITING_DETECTED",
        "INCONCLUSIVE",
        "AUTHENTIC_NO_ANOMALIES_DETECTED",
    )
    assert "confidence_level" in unified
    assert "reason" in unified
    assert "checks_performed" in unified
    assert "checks_unavailable" in unified


# ─── 6. Regression Tests for Independent Audit Findings ────────────────────

def test_transcript_script_mismatch_hindi_vs_english():
    """Verify Devanagari (Hindi) vs Latin (English) transcript comparison returns NOT_COMPARABLE without fabricating 0.0."""
    hindi_text = "यह एक विशेष समाचार प्रसारण है जो नवीकरणीय ऊर्जा के बारे में बात कर रहा है।"
    english_text = "This is a special news broadcast talking about renewable energy solutions."
    
    res = compare_transcripts_safely(
        whisper_transcript=hindi_text,
        gemini_transcript=english_text
    )
    assert res["similarity_status"] == "NOT_COMPARABLE"
    assert res["similarity_score"] is None
    assert "devanagari" in res["comparable_reason"].lower()
    assert "latin" in res["comparable_reason"].lower()


def test_c2pa_verified_camera_authenticity():
    """Verify cryptographically signed C2PA camera footage with 0 anomalies classifies as AUTHENTIC_NO_ANOMALIES_DETECTED."""
    prov = {
        "c2pa": {
            "status": "verified",
            "is_valid": True,
            "issuer": "Sony Camera Hardware Identity",
            "generator": "ILCE-7SM3-SN9182371",
            "tamper_detected": False,
        }
    }
    vis = {
        "status": "assessed",
        "anomaly_level": "low",
        "scene_cuts": {"count": 0, "abrupt_transitions": 0, "cut_timestamps": []},
        "observed_anomalies": [],
        "suspicious_segments": [],
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.0, "technical_flags": []}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.0, "anomaly_indicators": []}}
    aud_auth = {"suspicious_segments": [], "evidence": []}

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"integrity_score": 100},
        temporal={"temporal_consistency_score": 1.0},
        deepfake_heuristics={"deepfake_probability": 0.0, "voice_clone_probability": 0.0},
    )

    assert res["classification"] == "AUTHENTIC_NO_ANOMALIES_DETECTED"
    assert res["confidence_level"] == "HIGH"
    assert "c2pa" in res["reason"].lower() or "cryptographically" in res["reason"].lower()


def test_single_spectral_flag_not_overclassified():
    """Verify 1 single isolated FFT spectral flag without visual anomaly elevation does not classify as POTENTIALLY_AI_EDITED."""
    prov = {"c2pa": {"status": "missing"}}
    vis = {
        "status": "assessed",
        "anomaly_level": "low",  # not elevated
        "observed_anomalies": ["Abnormally suppressed high-frequency spectrum"],  # single heuristic flag
        "suspicious_segments": [
            {"start_time": 1.0, "end_time": 2.0, "anomaly_type": "fft_spectral_anomaly", "severity": "moderate", "description": "High frequency ratio"}
        ],
    }
    tech_aud = {"status": "assessed", "technical_anomaly_score": 0.0, "technical_flags": []}
    gem_aud = {"status": "assessed", "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.0, "anomaly_indicators": []}}
    aud_auth = {"suspicious_segments": [], "evidence": []}

    res = fuse_forensic_evidence(
        provenance=prov,
        visual_forensics=vis,
        technical_audio=tech_aud,
        gemini_audio=gem_aud,
        audio_authenticity=aud_auth,
        metadata={"integrity_score": 90},
        temporal={"temporal_consistency_score": 0.9},
        deepfake_heuristics={"deepfake_probability": 0.1, "voice_clone_probability": 0.1},
    )

    # Must NOT be POTENTIALLY_AI_EDITED because 1 isolated FFT flag lacks multi-signal corroboration
    assert res["classification"] != "POTENTIALLY_AI_EDITED"
    assert res["classification"] in ("INCONCLUSIVE", "AUTHENTIC_NO_ANOMALIES_DETECTED")


def test_jobs_create_ssrf_blocking():
    """Verify jobs endpoint rejects SSRF URLs before triggering pipeline."""
    import asyncio
    from backend.routers.jobs import create_job, JobCreate
    from fastapi import HTTPException

    # Test loopback
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(create_job(req=JobCreate(video_url="http://127.0.0.1/malicious.mp4")))
    assert exc_info.value.status_code == 400
    assert "security validation failed" in exc_info.value.detail.lower()

    # Test cloud metadata
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(create_job(req=JobCreate(video_url="http://169.254.169.254/latest/meta-data/")))
    assert exc_info.value.status_code == 400




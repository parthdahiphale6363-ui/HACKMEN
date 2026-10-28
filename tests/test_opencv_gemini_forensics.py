"""
test_opencv_gemini_forensics.py — Unit & Integration Tests for TrueLens Forensics
==================================================================================
Tests:
  - OpenCV visual stream forensics (audio-only, no-face, synthetic cuts, FFT, ELA)
  - Gemini multimodal audio forensics (missing key, quota/rate-limit, success, disclaimers)
  - Master forensics pipeline integration (typed schema compliance, score separation)
  - Intelligence dossier export formatting
"""

import os
import sys
import unittest
import tempfile
import numpy as np
import cv2
from unittest.mock import patch, MagicMock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.services.visual_forensics import (
    analyze_video_visual,
    _compute_fft_spectrum,
    _compute_ela_metrics,
)
from backend.services.gemini_audio import (
    analyze_audio_with_gemini,
    _compute_transcript_similarity,
)
from backend.services.forensics import run_forensics_pipeline
from backend.services.export_service import generate_markdown_dossier
from shared.schemas.forensics import OpenCVVisualForensics, GeminiAudioForensics


class TestOpenCVVisualForensics(unittest.TestCase):
    """Unit tests for OpenCV visual forensics module."""

    def test_audio_only_or_missing_file(self):
        """When input is audio-only or file missing, return status 'not_assessed' gracefully."""
        res_none = analyze_video_visual(None)
        self.assertEqual(res_none["status"], "not_assessed")
        self.assertIn("No local video file available", res_none["limitations"])

        res_missing = analyze_video_visual("non_existent_file_path.mp4")
        self.assertEqual(res_missing["status"], "not_assessed")

    def test_fft_spectrum_computation(self):
        """Verify 2D FFT spectral high-frequency ratio and regularity calculation."""
        # 1. Smooth low-frequency image
        smooth_img = np.ones((120, 120), dtype=np.uint8) * 128
        hf_smooth, reg_smooth, _ = _compute_fft_spectrum(smooth_img)
        self.assertLess(hf_smooth, 0.05)

        # 2. High-frequency noisy image
        noise_img = np.random.randint(0, 256, (120, 120), dtype=np.uint8)
        hf_noise, reg_noise, _ = _compute_fft_spectrum(noise_img)
        self.assertGreater(hf_noise, hf_smooth)

    def test_ela_computation_and_limitations(self):
        """Verify ELA calculation produces non-negative error values and proper caveats."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.circle(img, (50, 50), 30, (255, 255, 255), -1)
        mean_err, max_err, var = _compute_ela_metrics(img)
        self.assertGreaterEqual(mean_err, 0.0)
        self.assertGreaterEqual(max_err, 0.0)
        self.assertGreaterEqual(var, 0.0)

    def test_synthetic_video_analysis(self):
        """Creates a synthetic test video with 2 distinct scene cuts and verifies analysis."""
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, "test_synth.mp4")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(video_path, fourcc, 10.0, (160, 120))

        # Scene 1: Black frames (10 frames = 1.0s)
        for _ in range(10):
            frame = np.zeros((120, 160, 3), dtype=np.uint8)
            out.write(frame)

        # Scene 2: White frames with abrupt cut (10 frames = 1.0s)
        for _ in range(10):
            frame = np.ones((120, 160, 3), dtype=np.uint8) * 255
            out.write(frame)

        # Scene 3: Striped frames (10 frames = 1.0s)
        for _ in range(10):
            frame = np.zeros((120, 160, 3), dtype=np.uint8)
            frame[:, ::10] = 255
            out.write(frame)

        out.release()

        try:
            res = analyze_video_visual(video_path)
            self.assertEqual(res["status"], "assessed")
            self.assertGreaterEqual(res["frames_analyzed"], 2)
            self.assertEqual(res["video_resolution"], "160x120")
            # Should detect scene cuts between black, white, and striped scenes
            self.assertGreaterEqual(res["scene_cuts"]["count"] + res["scene_cuts"]["abrupt_transitions"], 1)
            # No human faces were present
            self.assertFalse(res["face_boundary_analysis"]["faces_detected"])
            self.assertIn("not_assessed", res["face_boundary_analysis"]["status"])
            # ELA applied
            self.assertTrue(res["error_level_analysis"]["applied"])
            # Schema validates cleanly
            schema = OpenCVVisualForensics(**res)
            self.assertEqual(schema.status, "assessed")
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)
            os.rmdir(temp_dir)


class TestGeminiAudioForensics(unittest.TestCase):
    """Unit tests for Gemini multimodal audio forensics module."""

    def test_missing_api_key_returns_not_assessed(self):
        """When GEMINI_API_KEY is not set, return status 'not_assessed' cleanly without crashing."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            # Create a dummy audio file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(b"dummy_audio_bytes")
                dummy_path = f.name
            try:
                res = analyze_audio_with_gemini(dummy_path, whisper_transcript="Hello world")
                self.assertEqual(res["status"], "not_assessed")
                self.assertIn("GEMINI_API_KEY", res["reason"])
                self.assertEqual(res["transcript_comparison"]["whisper_transcript"], "Hello world")
            finally:
                if os.path.exists(dummy_path):
                    os.remove(dummy_path)

    def test_missing_audio_file(self):
        """When audio file does not exist, return 'not_assessed'."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
            res = analyze_audio_with_gemini("non_existent_audio.mp3")
            self.assertEqual(res["status"], "not_assessed")

    def test_transcript_similarity_metric(self):
        """Test SequenceMatcher transcript similarity."""
        s1 = "The quick brown fox jumps over the lazy dog"
        s2 = "The quick brown fox jumps over the lazy dog"
        self.assertEqual(_compute_transcript_similarity(s1, s2), 1.0)

        s3 = "A fast red fox leaps across an energetic puppy"
        sim_low = _compute_transcript_similarity(s1, s3)
        self.assertLess(sim_low, 0.5)

    @patch("google.genai.Client")
    def test_gemini_audio_rate_limit_handling(self, mock_client_cls):
        """When Gemini returns a 429 quota error, handle it gracefully as status 'failed'."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.models.generate_content.side_effect = Exception("429 ResourceExhausted: Quota exceeded for model")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"dummy_mp3_content")
            audio_path = f.name

        try:
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
                res = analyze_audio_with_gemini(audio_path, whisper_transcript="Sample transcript")
                self.assertEqual(res["status"], "failed")
                self.assertIn("failed", res["reason"].lower())
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    @patch("google.genai.Client")
    def test_gemini_audio_mocked_success(self, mock_client_cls):
        """When Gemini API succeeds, parse structured findings and verify scientific disclaimer."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        mock_response = MagicMock()
        mock_response.text = """
        {
            "gemini_transcript": "Hello world, this is a test audio recording.",
            "discrepancies": ["whisper omitted audio recording"],
            "timestamp_notes": "Continuous speech cadence.",
            "cadence_observations": "Natural breath pauses between clauses.",
            "robotic_artifacts": "None observed.",
            "room_acoustics_consistent": true,
            "acoustic_anomalies": [],
            "voice_observations": ["Natural vocal tract acoustics"]
        }
        """
        mock_instance.models.generate_content.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"dummy_mp3_content")
            audio_path = f.name

        try:
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
                res = analyze_audio_with_gemini(audio_path, whisper_transcript="Hello world, this is a test")
                self.assertEqual(res["status"], "assessed")
                self.assertEqual(res["model_used"], "gemini-3.8-flash")
                self.assertGreater(res["transcript_comparison"]["similarity_score"], 0.70)
                self.assertEqual(res["transcript_comparison"]["discrepancies"], ["whisper omitted audio recording"])
                self.assertTrue(res["acoustic_anomaly_analysis"]["room_acoustics_consistent"])
                # Scientific guard assertion
                self.assertIn("No validated biometric voiceprint classifier", res["voice_clone_assessment"]["disclaimer"])
                # Validates schema
                schema = GeminiAudioForensics(**res)
                self.assertEqual(schema.status, "assessed")
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)


class TestForensicsPipelineIntegration(unittest.TestCase):
    """Integration test for master forensics pipeline and dossier export."""

    def test_run_forensics_pipeline_with_visual_and_audio(self):
        """Verify run_forensics_pipeline returns opencv_visual and gemini_audio fields."""
        transcript = "The global average temperature has steadily increased over the last fifty years."
        res = run_forensics_pipeline(
            transcript=transcript,
            video_url="https://www.youtube.com/watch?v=sample123",
            audio_path=None,
            video_path=None,
        )

        self.assertIn("opencv_visual", res)
        self.assertIn("gemini_audio", res)
        self.assertIn("technical_audio", res)
        self.assertIn("deepfake_analysis", res)
        self.assertIn("red_flags", res)

        # Status for unprovided video/audio should be not_assessed
        self.assertEqual(res["opencv_visual"]["status"], "not_assessed")
        self.assertEqual(res["gemini_audio"]["status"], "not_assessed")

    def test_export_markdown_dossier_formatting(self):
        """Verify dossier export includes OpenCV visual and Gemini audio sections."""
        forensics = {
            "deepfake_probability": 0.15,
            "voice_clone_probability": 0.10,
            "scene_consistency_score": 0.92,
            "red_flag_count": 0,
            "summary": "No anomalies detected.",
            "technical_audio": {"audio_stream_available": True, "codec_name": "aac", "sample_rate": 44100, "silence_burst_count": 1},
            "opencv_visual": {
                "status": "assessed",
                "detector_provenance": "OpenCV 5.0",
                "anomaly_level": "low",
                "frames_analyzed": 15,
                "video_resolution": "640x360",
                "video_duration_seconds": 15.0,
                "scene_cuts": {"count": 1, "abrupt_transitions": 0},
                "laplacian_blur": {"mean_variance": 85.0, "variance_stability": 0.75},
                "fft_spectral_analysis": {"high_frequency_ratio": 0.08, "spectral_regularity": 0.88},
                "face_boundary_analysis": {"faces_detected": False},
                "error_level_analysis": {"applied": True, "mean_error": 5.2, "variance": 14.0, "limitations": "ELA caveat."},
            },
            "gemini_audio": {
                "status": "assessed",
                "model_used": "gemini-2.5-flash",
                "transcript_comparison": {"similarity_score": 0.96, "discrepancies": []},
                "acoustic_anomaly_analysis": {"cadence_observations": "Natural rhythm", "robotic_artifacts": "None", "room_acoustics_consistent": True},
                "voice_clone_assessment": {"disclaimer": "No validated acoustic classifier."},
            }
        }

        dossier = generate_markdown_dossier(
            job_id="test-job-uuid",
            video_url="https://example.com/test.mp4",
            overall_verdict="Verified True",
            category="Genuine Video",
            confidence=92.0,
            breakdown={"total": 1, "true": 1, "false": 0, "misleading": 0, "unverifiable": 0},
            claims=[],
            forensics=forensics,
        )

        self.assertIn("OpenCV Computer Vision Stream Forensics", dossier)
        self.assertIn("Gemini Multimodal Audio Forensics & Cross-Verification", dossier)
        self.assertIn("2D FFT Spectral Distribution", dossier)
        self.assertIn("Whisper vs Gemini Transcript Concordance", dossier)
        self.assertIn("Scientific Guard", dossier)


if __name__ == "__main__":
    unittest.main()

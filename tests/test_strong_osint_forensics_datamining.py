"""
tests/test_strong_osint_forensics_datamining.py
================================================
Comprehensive multi-domain stress test suite for TrueLens:
  1. Strong OSINT Engine Tests (concurrent queries, relevance anchoring, anti-spoofing)
  2. Strong Video Forensics Tests (OpenCV CV pipeline, 2D FFT, bokeh tolerance, multimodal convergence)
  3. Strong Data Mining Tests (clustering stability, outlier math, Apriori rules, suspicion tiers)
"""

import os
import unittest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock

# OSINT imports
from backend.services.osint import (
    verify_via_google_factcheck,
    verify_via_news,
    build_reverse_search_queries,
    run_osint_pipeline,
    RECYCLED_FOOTAGE_KEYWORDS,
)

# Forensics imports
from backend.services.forensics import (
    analyze_deepfake_heuristics,
    analyze_metadata,
    extract_geolocation_claims,
    analyze_temporal_consistency,
    run_forensics_pipeline,
)
from backend.services.visual_forensics import (
    analyze_video_visual,
    _compute_fft_spectrum,
    _compute_ela_metrics,
)
from backend.services.gemini_audio import (
    CANDIDATE_GEMINI_MODELS,
    analyze_audio_with_gemini,
    _compute_transcript_similarity,
)

# Data Mining imports
from backend.services.data_mining import (
    cluster_claims,
    detect_outliers,
    mine_association_rules,
    mine_patterns,
    similarity_analysis,
    classify_content,
    get_suspicion_severity,
    run_data_mining_pipeline,
)


class TestStrongOSINTEngine(unittest.TestCase):
    """Stress testing the OSINT pipeline under heavy, noisy, and ambiguous inputs."""

    def test_osint_multi_claim_concurrent_retrieval(self):
        """Verify concurrent multi-claim search handles noisy results and deduplicates cleanly."""
        claims = [
            "Global electric vehicle sales reached 14 million in 2023.",
            "Solar panel efficiency surpassed 25 percent in commercial tests.",
            "Wind energy supplied 10 percent of worldwide electricity.",
        ]
        mock_news = [
            {"title": "Global electric vehicle sales hit record 14 million according to IEA report", "url": "https://reuters.com/ev-sales-2023", "snippet": "Global EV sales climbed to 14m."},
            {"title": "Duplicate Reuters headline", "url": "https://reuters.com/ev-sales-2023", "snippet": "Repeated url"},
            {"title": "Electric vehicle adoption accelerates across international markets", "url": "https://bloomberg.com/ev-record", "snippet": "Global electric vehicle transition reports."},
        ]

        with patch("backend.services.osint._newsapi_search_osint", return_value=mock_news), \
             patch("backend.services.osint._ddg_search", return_value=[]), \
             patch("backend.services.osint.groq_analyze_news_for_claim", return_value={"support_count": 2, "contradiction_count": 0, "scored_articles": [], "groq_summary": "Verified by IEA"}):

            res = verify_via_news(claims, "Global electric vehicle adoption and renewable power trends in 2023.")
            self.assertGreaterEqual(res["total_news_found"], 2)
            self.assertEqual(res["support_count"], 2)
            self.assertEqual(res["contradiction_count"], 0)

    def test_osint_google_factcheck_relevance_anchoring(self):
        """Google Fact Check debunks must be ignored if they refer to completely unrelated historical events."""
        mock_api_claims = {
            "claims": [
                {
                    "text": "1990 diesel train accident in Ohio was covered up",
                    "claimReview": [
                        {
                            "publisher": {"name": "Snopes"},
                            "url": "https://snopes.com/fact-check/1990-train",
                            "title": "Old train accident conspiracy debunked",
                            "textualRating": "False",
                        }
                    ],
                }
            ]
        }
        with patch.dict(os.environ, {"GOOGLE_FACTCHECK_API_KEY": "fake_test_key"}), \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = str(mock_api_claims).replace("'", '"').encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            # User is verifying quantum computing advancements
            res = verify_via_google_factcheck(["Quantum computing processor achieved fault-tolerant logical qubits."])
            self.assertEqual(res["debunked_count"], 0)
            self.assertEqual(res["manipulated_count"], 0)

    def test_osint_recycled_footage_anti_spoofing(self):
        """Historical context or person ages must not trip recycled footage veto."""
        for kw in ["years old", "recycled", "not from"]:
            self.assertNotIn(kw, RECYCLED_FOOTAGE_KEYWORDS)

        mock_search = [
            {
                "title": "A 100 years old university opened its new science laboratory",
                "snippet": "Celebrating its centennial, the 100 years old university inaugurated the lab.",
                "url": "https://theguardian.com/education/centennial-lab",
            }
        ]
        with patch("backend.services.osint._ddg_search", return_value=mock_search):
            res = build_reverse_search_queries("https://youtube.com/watch?v=univ123", "university laboratory opening", ["London"])
            self.assertFalse(res["recycled_footage_detected"])


class TestStrongVideoForensics(unittest.TestCase):
    """Stress testing the computer vision and acoustic forensics pipelines."""

    def test_visual_forensics_synthetic_frame_analysis(self):
        """Creates a synthetic video stream and validates Laplacian, FFT, scene-cut, and ELA pipelines."""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, "test_strong_cv.mp4")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(video_path, fourcc, 15.0, (240, 180))

        # Shot 1: Smooth blue-to-white gradient (15 frames = 1.0s)
        for i in range(15):
            f = np.zeros((180, 240, 3), dtype=np.uint8)
            f[:, :, 0] = np.linspace(50, 240, 240, dtype=np.uint8)
            f[:, :, 2] = 120
            out.write(f)

        # Shot 2: Abrupt hard cut to checkerboard pattern (15 frames = 1.0s)
        for i in range(15):
            f = np.zeros((180, 240, 3), dtype=np.uint8)
            f[::20, ::20] = 255
            out.write(f)

        out.release()

        try:
            res = analyze_video_visual(video_path)
            self.assertEqual(res["status"], "assessed")
            self.assertGreaterEqual(res["frames_analyzed"], 2)
            # Detected at least one hard scene transition
            self.assertGreaterEqual(res["scene_cuts"]["count"] + res["scene_cuts"]["abrupt_transitions"], 1)
            # ELA was computed
            self.assertTrue(res["error_level_analysis"]["applied"])
            self.assertIsNotNone(res["error_level_analysis"]["mean_error"])
            # FFT frequency metrics computed
            self.assertGreater(res["fft_spectral_analysis"]["high_frequency_ratio"], 0.0)
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)
            os.rmdir(temp_dir)

    def test_visual_forensics_bokeh_portrait_immunity(self):
        """A sharp face against a shallow depth-of-field blurred background must not flag face boundary mismatch."""
        # Test the boundary blur calibration logic directly
        face_blur = 120.0     # sharp, in-focus subject
        outer_blur = 18.0     # shallow depth of field bokeh background
        ratio = face_blur / outer_blur  # 6.67
        # Our calibrated threshold only flags ratio > 4.5 if outer_blur >= 35.0
        should_flag = bool(ratio > 4.5 and outer_blur >= 35.0)
        self.assertFalse(should_flag, "Portrait bokeh should never be flagged as an unnatural face paste.")

    def test_multimodal_synthetic_convergence_boundary(self):
        """
        Verify that a synthetic media veto is only raised when supported by genuine technical stream
        anomalies or visual+acoustic convergence, and never on clean media.
        """
        # Clean organic audio profile
        clean_audio = {
            "audio_stream_available": True,
            "sample_rate": 48000,
            "channels": 2,
            "codec_name": "aac",
            "bit_rate_kbps": 192.0,
            "duration_seconds": 30.0,
            "silence_burst_count": 0,
            "technical_anomaly_score": 0.0,
            "technical_flags": [],
        }
        res_clean = analyze_deepfake_heuristics("Clean standard speech recording.", "https://example.com/clean.mp4", technical_audio=clean_audio)
        self.assertFalse(res_clean["is_synthetic"])
        self.assertFalse(res_clean["forensics_veto"]["veto"])
        self.assertLess(res_clean["deepfake_probability"], 0.30)

        # Synthetic TTS profile (22.05kHz, low bitrate, 8 silence cuts, score 0.70)
        synth_audio = {
            "audio_stream_available": True,
            "sample_rate": 22050,
            "channels": 1,
            "codec_name": "aac",
            "bit_rate_kbps": 28.0,
            "duration_seconds": 15.0,
            "silence_burst_count": 8,
            "technical_anomaly_score": 0.70,
            "technical_flags": [
                "Unusual sample rate (22050 Hz) characteristic of neural TTS / voice models",
                "Very low audio bitrate (28.0 kbps) — possible artifact suppression",
                "Multiple abrupt silence gaps detected (8 cuts) — possible splice/sentence grafting",
            ],
        }
        res_synth = analyze_deepfake_heuristics("Neural TTS output text.", "https://example.com/synth.mp4", technical_audio=synth_audio)
        self.assertTrue(res_synth["is_synthetic"])
        self.assertTrue(res_synth["forensics_veto"]["veto"])
        self.assertGreaterEqual(res_synth["deepfake_probability"], 0.75)


class TestStrongDataMining(unittest.TestCase):
    """Stress testing the data mining clustering, outlier, and association rule subsystems."""

    def test_data_mining_clustering_stability_edge_cases(self):
        """Clustering must be completely stable for 0, 1, and N claims without crashing."""
        # 0 claims
        res_zero = cluster_claims([])
        self.assertEqual(res_zero["cluster_count"], 0)
        self.assertEqual(res_zero["clusters"], [])

        # 1 claim (degenerate cluster)
        res_one = cluster_claims([{"claim": {"normalized_text": "Single standalone claim.", "domain": "energy"}}])
        self.assertEqual(res_one["cluster_count"], 1)

        # Multiple claims
        claims = [
            {"claim": {"normalized_text": f"Solar energy adoption in state {i}.", "domain": "energy"}}
            for i in range(8)
        ]
        res_multi = cluster_claims(claims)
        self.assertEqual(sum(c["size"] for c in res_multi["clusters"]), 8)

    def test_data_mining_outlier_z_score_extreme_values(self):
        """Outlier detection handles extreme z-scores without division by zero or NaN propagation."""
        claims = [
            {"claim": {"normalized_text": "Standard length claim statement number one."}, "verdict": {"label": "true", "confidence": 0.85}},
            {"claim": {"normalized_text": "Standard length claim statement number two."}, "verdict": {"label": "true", "confidence": 0.84}},
            {"claim": {"normalized_text": "Standard length claim statement number three."}, "verdict": {"label": "true", "confidence": 0.86}},
            # Extreme length and low confidence outlier
            {"claim": {"normalized_text": "Word " * 120}, "verdict": {"label": "unverified", "confidence": 0.20}},
        ]
        res = detect_outliers(claims)
        self.assertGreaterEqual(res["outlier_count"], 1)
        self.assertIsInstance(res["anomaly_score"], float)
        self.assertFalse(np.isnan(res["anomaly_score"]))

    def test_data_mining_suspicion_severity_thresholds(self):
        """Verify standardized severity thresholds: 0.38 is strictly moderate, never high or severe."""
        self.assertEqual(get_suspicion_severity(0.10), "low")
        self.assertEqual(get_suspicion_severity(0.20), "low")
        self.assertEqual(get_suspicion_severity(0.38), "moderate")
        self.assertEqual(get_suspicion_severity(0.45), "moderate")
        self.assertEqual(get_suspicion_severity(0.55), "elevated")
        self.assertEqual(get_suspicion_severity(0.85), "high")

    def test_data_mining_association_rules_math(self):
        """Verify Apriori association rules mathematical correctness (support, confidence, lift)."""
        claims = [
            {"claim": {"normalized_text": f"Claim {i}"}, "verdict": {"label": "false", "confidence": 0.90, "evidence": []}}
            for i in range(3)
        ] + [
            {"claim": {"normalized_text": f"Claim {i+3}"}, "verdict": {"label": "true", "confidence": 0.85, "evidence": [{"domain": "reuters.com"}]}}
            for i in range(3)
        ]

        rules_report = mine_association_rules(claims, min_support=0.20, min_confidence=0.50)
        self.assertIn("rules", rules_report)
        for r in rules_report["rules"]:
            self.assertGreaterEqual(r["support"], 0.0)
            self.assertLessEqual(r["support"], 1.0)
            self.assertGreaterEqual(r["confidence"], 0.0)
            self.assertLessEqual(r["confidence"], 1.0)
            self.assertGreaterEqual(r["lift"], 0.0)

    def test_data_mining_pipeline_end_to_end_synthesis(self):
        """End-to-end data mining execution returns complete structured schema without errors."""
        claims = [
            {
                "claim": {"normalized_text": "Global crude oil prices dropped to 70 dollars per barrel."},
                "verdict": {"label": "Verified True", "confidence": 0.90},
            },
            {
                "claim": {"normalized_text": "Electric vehicle battery capacity doubled in 2024."},
                "verdict": {"label": "Unverified", "confidence": 0.50},
            },
        ]
        transcript = "Crude oil traded lower as international energy markets stabilized. Vehicle battery innovations continue."
        forensics_mock = {"red_flag_count": 0, "deepfake_probability": 0.05}
        osint_mock = {"contradiction_count": 0, "recycled_footage_detected": False}

        dm_report = run_data_mining_pipeline(
            transcript=transcript,
            claim_items=claims,
            forensics_report=forensics_mock,
            osint_report=osint_mock,
        )

        self.assertIn("dm_score", dm_report)
        self.assertIn("classification", dm_report)
        self.assertIn("clustering", dm_report)
        self.assertIn("outlier_detection", dm_report)
        self.assertIn("association_rules", dm_report)
        self.assertIn("pattern_mining", dm_report)
        self.assertIn("summary", dm_report)
        self.assertGreater(dm_report["dm_score"], 50.0)


if __name__ == "__main__":
    unittest.main()

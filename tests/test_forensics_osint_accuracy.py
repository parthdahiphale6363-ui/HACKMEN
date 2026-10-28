"""
tests/test_forensics_osint_accuracy.py
======================================
Regression and accuracy test suite for TrueLens Multimodal Forensics & OSINT Engine:
  1. Gemini Audio Model selection and resilience
  2. Transcript reporting/discussion of deepfakes does NOT falsely flag is_synthetic
  3. Age mentions ("25 years old") do NOT trigger recycled footage veto
  4. Google Fact Check requires topic overlap before vetoing
  5. Geolocation word boundary extraction prevents false sub-string matches
  6. Visual Forensics tolerates camera bokeh / portrait mode without false face paste alarms
  7. Multimodal synthetic veto synthesis
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from backend.services.forensics import (
    analyze_deepfake_heuristics,
    extract_geolocation_claims,
    run_forensics_pipeline,
)
from backend.services.osint import (
    build_reverse_search_queries,
    verify_via_google_factcheck,
    run_osint_pipeline,
    RECYCLED_FOOTAGE_KEYWORDS,
)
from backend.services.visual_forensics import (
    _compute_fft_spectrum,
    analyze_video_visual,
)
from backend.services.gemini_audio import (
    CANDIDATE_GEMINI_MODELS,
    analyze_audio_with_gemini,
)


class TestGeminiAudioModelSelection(unittest.TestCase):
    def test_gemini_candidate_models(self):
        """Verify models include current active models (gemini-3.8-flash, gemini-3-flash-preview) and avoid deprecated 2.5."""
        self.assertIn("gemini-3.8-flash", CANDIDATE_GEMINI_MODELS)
        self.assertIn("gemini-3-flash-preview", CANDIDATE_GEMINI_MODELS)
        self.assertNotIn("gemini-2.5-flash", CANDIDATE_GEMINI_MODELS)

    def test_gemini_audio_graceful_missing_key(self):
        """Verify graceful fallback when GEMINI_API_KEY is unset and audio file exists."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
            tf.write(b"ID3dummy-audio-bytes")
            temp_path = tf.name

        try:
            with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
                res = analyze_audio_with_gemini(temp_path, whisper_transcript="test transcript")
                self.assertEqual(res["status"], "not_assessed")
                self.assertIn("not configured", res["reason"].lower())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestDeepfakeHeuristicsAccuracy(unittest.TestCase):
    def test_news_discussion_of_deepfakes_not_synthetic(self):
        """
        News report discussing deepfakes or manipulation should NOT trigger is_synthetic.
        """
        news_transcript = (
            "Today on Fact Check News: Critics on social media claimed that a viral video was edited, "
            "alleging that the lip sync is off and the recording was manipulated. "
            "However, forensic analysts confirmed the original video was authentic and unmodified."
        )
        tech_clean = {
            "technical_anomaly_score": 0.05,
            "technical_flags": [],
            "sample_rate": 44100,
        }
        res = analyze_deepfake_heuristics(news_transcript, "https://youtube.com/watch?v=123", technical_audio=tech_clean)

        # Base deepfake probability should remain low/moderate, and NOT trigger synthetic veto
        self.assertFalse(res["is_synthetic"])
        self.assertFalse(res["forensics_veto"]["veto"])
        self.assertLess(res["deepfake_probability"], 0.60)


class TestOSINTAccuracyAndRecycledFootage(unittest.TestCase):
    def test_years_old_person_not_recycled_footage(self):
        """
        Articles describing a person's age (e.g. '25 years old student') must not trigger recycled footage veto.
        """
        for kw in RECYCLED_FOOTAGE_KEYWORDS:
            self.assertNotEqual(kw, "years old")
            self.assertNotEqual(kw, "recycled")

        mock_results = [
            {
                "title": "A 25 years old student won the state mathematics championship",
                "snippet": "The 25 years old scholar was awarded in New Delhi today for outstanding research.",
                "url": "https://thehindu.com/news/national/student-award",
            }
        ]
        with patch("backend.services.osint._ddg_search", return_value=mock_results):
            res = build_reverse_search_queries("https://youtube.com/watch?v=abc", "student championship", ["Delhi"])
            self.assertFalse(res["recycled_footage_detected"])
            self.assertFalse(res["potential_recycled_content"])

    def test_google_factcheck_anchored_by_title_relevance(self):
        """
        Google fact checks with low keyword/topic overlap must NOT count towards debunked_count or veto.
        """
        mock_api_response = {
            "claims": [
                {
                    "text": "1994 vintage diesel locomotive broke down in Chicago",
                    "claimReview": [
                        {
                            "publisher": {"name": "AFP Fact Check"},
                            "url": "https://factcheck.afp.com/unrelated",
                            "title": "Old diesel locomotive breakdown photo falsely claimed to be in London",
                            "textualRating": "False",
                        }
                    ]
                }
            ]
        }
        with patch.dict(os.environ, {"GOOGLE_FACTCHECK_API_KEY": "test_fake_key"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.read.return_value = str(mock_api_response).replace("'", '"').encode("utf-8")
                mock_urlopen.return_value.__enter__.return_value = mock_resp

                # User's actual claim is completely unrelated
                res = verify_via_google_factcheck(["Solar panels generate electricity at record efficiency in 2026"])
                # Since overlap is low, debunked_count must be 0
                self.assertEqual(res["debunked_count"], 0)
                self.assertFalse(any(fc["is_debunk"] for fc in res["fact_checks_found"]))


class TestGeolocationWordBoundaries(unittest.TestCase):
    def test_strict_word_boundaries_for_countries(self):
        """
        Transcript mentioning 'ukraine' or 'duke' must not falsely match country 'uk'.
        """
        transcript = "The Duke of Wellington visited Ukraine to inspect agricultural grain exports."
        res = extract_geolocation_claims(transcript)
        countries = [c.lower() for c in res["countries"]]
        self.assertIn("ukraine", countries)
        self.assertNotIn("uk", countries)
        self.assertFalse(res["potential_misattribution"])


class TestVisualForensicsThresholds(unittest.TestCase):
    def test_fft_spectral_calibration(self):
        """Natural video frame gradient should not trigger elevated frequency anomaly flag."""
        y, x = np.mgrid[0:240, 0:320]
        gray = ((np.sin(x / 20.0) + np.cos(y / 20.0) + 2) * 60).astype(np.uint8)
        hf_ratio, regularity, flags = _compute_fft_spectrum(gray)
        self.assertLess(hf_ratio, 0.52)
        self.assertNotIn("Elevated high-frequency energy pattern (possible artificial synthesis / noise overlay)", flags)


class TestMultimodalSyntheticVeto(unittest.TestCase):
    def test_clean_audio_and_clean_visual_never_vetoed(self):
        """Clean video stream and clean audio stream must yield is_synthetic=False."""
        with patch("backend.services.forensics.analyze_audio_stream") as mock_audio, \
             patch("backend.services.forensics.analyze_video_visual") as mock_visual, \
             patch("backend.services.forensics.analyze_audio_with_gemini") as mock_gemini, \
             patch("backend.services.forensics._call_groq", return_value=None):

            mock_audio.return_value = {
                "technical_anomaly_score": 0.0,
                "technical_flags": [],
            }
            mock_visual.return_value = {
                "status": "assessed",
                "anomaly_level": "low",
                "observed_anomalies": [],
            }
            mock_gemini.return_value = {
                "status": "assessed",
                "acoustic_anomaly_analysis": {"acoustic_anomaly_score": 0.05, "anomaly_indicators": []},
            }

            res = run_forensics_pipeline("This is a verified news broadcast about renewable energy.", "https://youtube.com/watch?v=xyz")
            self.assertFalse(res["is_synthetic"])
            self.assertFalse(res["forensics_veto"]["veto"])
            self.assertGreater(res["video_integrity_score"], 80.0)


if __name__ == "__main__":
    unittest.main()

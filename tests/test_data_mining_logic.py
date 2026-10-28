"""
test_data_mining_logic.py — Comprehensive Unit & Integration Tests for TrueLens Data Mining
===========================================================================================
Validates:
  1. Empty patterns and clean organic discourse handling
  2. Contextual warning explanation when no patterns are found but external evidence warns
  3. Insufficient data handling (empty text, single claim, zero claims)
  4. Contradictory signals:
     - Sensational language with verified TRUE claims
     - Formal language with verified FALSE claims
  5. Validated suspicion thresholds (ensuring 0.38 is strictly "moderate", never "severe")
  6. Distinction between pattern confidence and verdict confidence
  7. Genuine mathematical computation for association rules, clustering, and outlier detection
  8. Transparent multi-signal uncertainty weighting (without claiming statistical calibration)
"""

import math
import pytest
from backend.services.data_mining import (
    classify_content,
    cluster_claims,
    detect_outliers,
    mine_association_rules,
    mine_patterns,
    similarity_analysis,
    run_data_mining_pipeline,
    get_suspicion_severity,
    THRESHOLD_LOW,
    THRESHOLD_MODERATE,
    THRESHOLD_ELEVATED,
)
from backend.services.job_service import compute_overall_verdict


# ─── 1. Validated Suspicion Thresholds ────────────────────────────────────────

def test_validated_suspicion_thresholds_severity():
    """Verify that suspicion scores map strictly to validated thresholds, and 0.38 is never severe."""
    # Strict requirement: 0.38 must be 'moderate', NOT 'severe' or 'high'
    assert get_suspicion_severity(0.38) == "moderate"

    # Boundary tests
    assert get_suspicion_severity(0.00) == "low"
    assert get_suspicion_severity(0.15) == "low"
    assert get_suspicion_severity(THRESHOLD_LOW) == "low"

    assert get_suspicion_severity(0.21) == "moderate"
    assert get_suspicion_severity(0.35) == "moderate"
    assert get_suspicion_severity(THRESHOLD_MODERATE) == "moderate"

    assert get_suspicion_severity(0.46) == "elevated"
    assert get_suspicion_severity(0.60) == "elevated"
    assert get_suspicion_severity(THRESHOLD_ELEVATED) == "elevated"

    assert get_suspicion_severity(0.71) == "high"
    assert get_suspicion_severity(0.95) == "high"
    assert get_suspicion_severity(1.00) == "high"


# ─── 2. Empty Patterns & Clean Discourse ─────────────────────────────────────

def test_empty_patterns_and_clean_discourse():
    """Verify that standard, clean discourse produces zero suspicious patterns and low anomaly."""
    transcript = (
        "The atmospheric greenhouse effect warms the planet by trapping infrared radiation. "
        "Carbon dioxide and methane absorb longwave radiation emitted from the Earth's surface, "
        "which has been verified by atmospheric spectroscopy experiments over the past century."
    )
    claim_items = [
        {
            "claim": {"normalized_text": "The greenhouse effect warms the planet by trapping infrared radiation."},
            "verdict": {"label": "true", "confidence": 0.94, "evidence": [{"domain": "nature.com", "relevance_score": 0.95}]},
        },
        {
            "claim": {"normalized_text": "Carbon dioxide absorbs longwave radiation from Earth's surface."},
            "verdict": {"label": "true", "confidence": 0.92, "evidence": [{"domain": "nasa.gov", "relevance_score": 0.90}]},
        },
    ]

    report = run_data_mining_pipeline(
        transcript=transcript,
        claim_items=claim_items,
        forensics_report={"red_flag_count": 0, "deepfake_probability": 0.05},
        osint_report={"contradiction_count": 0, "potential_recycled_content": False},
    )

    # Patterns should be completely clean
    assert report["pattern_mining"]["pattern_count"] == 0
    assert report["outlier_detection"]["outlier_count"] == 0
    assert report["classification"]["suspicion_severity"] == "low"
    assert report["classification"]["suspicion_score"] <= THRESHOLD_LOW
    assert "Low Anomaly" in report["classification"]["category"] or "Consistent" in report["classification"]["category"]
    assert "consistent with standard organic discourse" in report["summary"].lower()


# ─── 3. Contextual Warning Explanation When No DM Patterns Found ─────────────

def test_no_suspicious_patterns_explains_external_evidence_warnings():
    """If no DM patterns are found, the summary must explain which external evidence supports warnings."""
    clean_transcript = "The city council held its monthly budgetary session on Tuesday evening at city hall."
    clean_claims = [
        {
            "claim": {"normalized_text": "The city council held its monthly session on Tuesday."},
            "verdict": {"label": "unverifiable", "confidence": 0.50, "evidence": []},
        }
    ]

    # External warnings: Forensics has red flags and OSINT has recycled footage
    forensics_warning = {"red_flag_count": 3, "deepfake_probability": 0.78}
    osint_warning = {"contradiction_count": 2, "recycled_footage_detected": True}

    report = run_data_mining_pipeline(
        transcript=clean_transcript,
        claim_items=clean_claims,
        forensics_report=forensics_warning,
        osint_report=osint_warning,
    )

    # DM text patterns should be 0
    assert report["pattern_mining"]["pattern_count"] == 0
    # Summary must explicitly explain that warnings stem from external evidence
    summary_lower = report["summary"].lower()
    assert "no suspicious linguistic or structural data mining patterns detected" in summary_lower
    assert "technical media stream forensics anomalies" in summary_lower or "external osint" in summary_lower


# ─── 4. Insufficient Data Handling ───────────────────────────────────────────

def test_insufficient_data_empty_transcript_and_claims():
    """Verify that completely empty inputs do not crash and degrade gracefully."""
    report = run_data_mining_pipeline(
        transcript="",
        claim_items=[],
        forensics_report={},
        osint_report={},
    )

    assert report["clustering"]["cluster_count"] == 0
    assert report["outlier_detection"]["outlier_count"] == 0
    assert report["association_rules"]["total_rules"] == 0
    assert report["pattern_mining"]["pattern_count"] == 0
    assert report["similarity_analysis"]["total_matches"] == 0
    assert report["classification"]["category"] == "Insufficient Pattern Data"
    assert report["classification"]["pattern_confidence"] <= 0.30
    assert report["dm_veto"]["veto"] is False


def test_insufficient_data_single_claim():
    """Verify single-claim edge case computes 1 cluster, 0 outliers, 0 association rules without crash."""
    single_claim = [
        {
            "claim": {"normalized_text": "Water freezes at 0 degrees Celsius."},
            "verdict": {"label": "true", "confidence": 0.95, "evidence": []},
        }
    ]
    report = run_data_mining_pipeline(
        transcript="Water freezes at zero degrees Celsius.",
        claim_items=single_claim,
        forensics_report={},
        osint_report={},
    )

    assert report["clustering"]["cluster_count"] == 1
    assert report["outlier_detection"]["outlier_count"] == 0  # Cannot compute outliers with N=1
    assert report["association_rules"]["total_rules"] == 0    # Cannot compute Apriori rules with N=1
    assert report["dm_score"] >= 70.0


# ─── 5. Contradictory Signals: Sensationalism vs Verified Truth ──────────────

def test_contradictory_signals_sensational_language_with_verified_true_claims():
    """
    Sensational clickbait wording ('shocking, urgent bombshell') but claims are verified TRUE.
    Data mining must flag linguistic anomaly, but NEVER override verified claim evidence to call it Fake.
    """
    transcript = (
        "Shocking urgent bombshell alert! Doctors confirmed that the human body requires daily hydration. "
        "This unbelievable truth was proven in catastrophic heatwave studies."
    )
    claim_items = [
        {
            "claim": {"normalized_text": "The human body requires daily hydration to survive."},
            "verdict": {"label": "true", "confidence": 0.95, "evidence": [{"domain": "who.int", "relevance_score": 0.98}]},
        },
        {
            "claim": {"normalized_text": "Heatwaves increase the biological requirement for water."},
            "verdict": {"label": "true", "confidence": 0.92, "evidence": [{"domain": "cdc.gov", "relevance_score": 0.95}]},
        },
    ]

    report = run_data_mining_pipeline(
        transcript=transcript,
        claim_items=claim_items,
        forensics_report={"red_flag_count": 0, "deepfake_probability": 0.0},
        osint_report={"contradiction_count": 0},
    )

    # DM correctly detects sensational pattern
    assert report["pattern_mining"]["pattern_count"] >= 1
    assert any(p["pattern"] == "Emotional Intensifiers" for p in report["pattern_mining"]["patterns"])

    # But DM must NOT declare it "Fake" or "Debunked"
    assert "Debunked" not in report["classification"]["category"]
    assert "Fake" not in report["classification"]["category"]
    assert report["dm_veto"]["veto"] is False

    # Base overall verdict must remain True based on verified claim evidence
    overall = compute_overall_verdict(claim_items, dm_report=report)
    assert overall["final_verdict_category"] in ("Genuine", "Likely Genuine")
    assert "True" in overall["overall_verdict"]


# ─── 6. Contradictory Signals: Calm Academic Language vs Verified False Claims 

def test_contradictory_signals_calm_language_with_verified_false_claims():
    """
    Calm, formal academic language, but claims are verified FALSE.
    Data mining notes low linguistic anomaly, but overall verdict is Fake based on claim evidence.
    """
    transcript = (
        "In accordance with classical thermodynamic investigations, perpetual motion engines of the second kind "
        "spontaneously generate infinite energy without thermodynamic entropy production."
    )
    claim_items = [
        {
            "claim": {"normalized_text": "Perpetual motion engines spontaneously generate infinite energy."},
            "verdict": {"label": "false", "confidence": 0.98, "evidence": [{"domain": "physics.org", "stance": "contradicts"}]},
        }
    ]

    report = run_data_mining_pipeline(
        transcript=transcript,
        claim_items=claim_items,
        forensics_report={},
        osint_report={},
    )

    # Linguistic pattern mining sees no sensational words
    assert sum(1 for p in report["pattern_mining"]["patterns"] if p["pattern"] == "Emotional Intensifiers") == 0

    # Overall verdict is driven by empirical fact-checking evidence
    overall = compute_overall_verdict(claim_items, dm_report=report)
    assert overall["final_verdict_category"] == "Fake"
    assert "False" in overall["overall_verdict"]


# ─── 7. Actual Association Rules Mathematics ──────────────────────────────────

def test_actual_association_rules_math():
    """Verify that Association Rules support, confidence, and lift follow exact probability formulas."""
    claims = [
        {"claim": {"normalized_text": f"Claim {i}"}, "verdict": {"label": "false", "confidence": 0.90, "evidence": []}}
        for i in range(3)
    ] + [
        {"claim": {"normalized_text": f"Claim {i+3}"}, "verdict": {"label": "true", "confidence": 0.85, "evidence": [{"domain": "reuters.com"}]}}
        for i in range(3)
    ]

    rules_report = mine_association_rules(claims, min_support=0.20, min_confidence=0.50)
    rules = rules_report["rules"]
    assert len(rules) > 0

    for r in rules:
        # Support = P(A and B) must be in (0, 1]
        assert 0.0 < r["support"] <= 1.0
        # Confidence = P(B | A) must be in (0, 1]
        assert 0.0 < r["confidence"] <= 1.0
        # Lift must be non-negative
        assert r["lift"] >= 0.0

        # Specific rule check: All 3 false claims have evidence=none
        if r["antecedent"] == "verdict=false" and r["consequent"] == "evidence=none":
            # 3 out of 6 claims have both -> Support = 0.5
            assert math.isclose(r["support"], 0.5, abs_tol=0.01)
            # All false claims have evidence=none -> Confidence = 1.0
            assert math.isclose(r["confidence"], 1.0, abs_tol=0.01)
            # P(evidence=none) = 3/6 = 0.5 -> Lift = 1.0 / 0.5 = 2.0
            assert math.isclose(r["lift"], 2.0, abs_tol=0.01)


# ─── 8. Outlier Detection Mathematics ─────────────────────────────────────────

def test_actual_outlier_detection_z_score():
    """Verify that outlier detection only flags claims with statistically significant z-scores."""
    # 5 claims with normal confidence around 0.80, and one extreme outlier at 0.15
    claim_items = [
        {"claim": {"normalized_text": f"Normal claim {i}"}, "verdict": {"label": "true", "confidence": 0.80, "evidence": [{"domain": "test.com"}]}}
        for i in range(5)
    ]
    # Add outlier claim
    claim_items.append({
        "claim": {"normalized_text": "Anomalous low confidence claim"},
        "verdict": {"label": "true", "confidence": 0.15, "evidence": []},
    })

    outlier_res = detect_outliers(claim_items)
    assert outlier_res["outlier_count"] >= 1
    flagged = outlier_res["outliers"][0]
    assert flagged["claim_index"] == 5
    assert any("z" in r.lower() or "confidence" in r.lower() for r in flagged["reasons"])


# ─── 9. Transparent Multi-Signal Uncertainty Weighting ───────────────────────

def test_transparent_signal_weighting_without_false_calibration_claims():
    """Verify transparent signal weighting adjusts confidences without claiming formal statistical calibration."""
    claim_items = [
        {
            "claim": {"normalized_text": "This cure was suppressed by doctors and big pharma."},
            "verdict": {"label": "unverified", "confidence": 0.80, "evidence": []},
        }
    ]
    report = run_data_mining_pipeline(
        transcript="This cure was suppressed by doctors and big pharma. Share before deleted.",
        claim_items=claim_items,
        forensics_report={},
        osint_report={},
    )

    # Uncertainty discount was applied
    assert report["signal_weighted_claims_count"] >= 1
    assert report["calibrated_claims_count"] >= 1  # Backward compatibility alias
    assert claim_items[0]["verdict"]["confidence"] < 0.80
    assert claim_items[0]["verdict"].get("signal_weighting_applied") is True
    # Summary accurately describes multi-signal uncertainty weighting
    assert "uncertainty weighting" in report["summary"].lower()

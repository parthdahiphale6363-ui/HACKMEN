"""
Regression and Integration Tests for TrueLens Claim Extraction & Verdict Logic:
1. Petrol example regression: prevents atomic claim splitting from producing incomplete fragments
   such as 'The petrol being sold costs Rs.' and '120 per unit.'
2. Complete propositions, numbers, currencies (Rs., $, €, ₹), and units (km/h, per unit, %) preservation
3. Ambiguity and conflicting prices / contradictory statement detection
4. Epistemic verdict taxonomy (UNVERIFIED vs MISLEADING vs FALSE vs TRUE)
5. Metric isolation: source relevance, evidence support, source acceptance, verdict confidence, consensus
"""

import pytest
from shared.schemas.verdict import VerdictLabel, Evidence, Verdict, AtomicClaimAssessment
from backend.services.job_service import (
    decompose_compound_claim,
    detect_claim_ambiguity,
    validate_claim_for_verification,
    split_sentences_safely,
    is_complete_proposition,
    compute_overall_verdict,
    fuse_scores,
    clean_and_filter_claims,
)
from pipeline.search import _canonical_verdict_label
from pipeline.evidence_classifier import (
    compute_consensus_and_metrics,
    compute_calibrated_confidence,
    ClassifiedEvidenceItem,
    EvidenceStance,
)


# ─── 1. PETROL EXAMPLE REGRESSION TEST ────────────────────────────────────────

def test_petrol_claim_not_split_into_broken_fragments():
    """
    REGRESSION:
    'The petrol being sold costs Rs. 120 per unit.' must NOT be split into
    'The petrol being sold costs Rs.' and '120 per unit.'.
    It must be preserved as a single intact proposition.
    """
    claim = "The petrol being sold costs Rs. 120 per unit."
    atoms = decompose_compound_claim(claim)
    
    assert len(atoms) == 1, f"Expected 1 atomic proposition, got: {atoms}"
    assert atoms[0] == "The petrol being sold costs Rs. 120 per unit."
    assert not any(a.endswith("Rs.") for a in atoms)
    assert not any(a.startswith("120 per unit") for a in atoms)


def test_petrol_claim_preflight_validation():
    """Pre-flight validation passes and preserves currency and unit."""
    claim = "The petrol being sold costs Rs. 120 per unit."
    val = validate_claim_for_verification(claim)
    assert val["valid"] is True
    assert "Rs. 120 per unit" in val["sanitized_claim"]


# ─── 2. CURRENCY, QUANTITY & UNIT PRESERVATION ────────────────────────────────

@pytest.mark.parametrize("claim_text, expected_currency_or_unit", [
    ("The company paid $1,500 per month to each contractor.", "$1,500 per month"),
    ("Crude oil dropped to €85 per barrel in European exchanges.", "€85 per barrel"),
    ("Retail petrol was fixed at ₹95 per litre across the state.", "₹95 per litre"),
    ("The high-speed train reached 120 km/h during trials.", "120 km/h"),
    ("The automobile uses a 40% ethanol blend fuel.", "40% ethanol"),
    ("Dr. Smith confirmed the medicine costs USD. 50 per vial.", "USD. 50 per vial"),
])
def test_currency_and_unit_preservation(claim_text, expected_currency_or_unit):
    """Numbers, currencies, and units must remain bound to their propositions."""
    atoms = decompose_compound_claim(claim_text)
    assert len(atoms) >= 1
    # Check that the number and unit were not separated into distinct fragments
    assert any(expected_currency_or_unit in a for a in atoms)
    # Check that no atom is an incomplete dangling fragment
    for a in atoms:
        assert is_complete_proposition(a)


def test_safe_sentence_splitter_protects_abbreviations():
    """split_sentences_safely must not break on Rs., Dr., approx., or decimals."""
    text = "The petrol costs Rs. 120. Dr. Rao verified approx. 50% increase."
    sentences = split_sentences_safely(text)
    assert len(sentences) == 2
    assert sentences[0] == "The petrol costs Rs. 120."
    assert "Dr. Rao" in sentences[1]
    assert "approx. 50%" in sentences[1]


# ─── 3. AMBIGUITY & CONFLICTING PRICE DETECTION ──────────────────────────────

def test_detect_claim_ambiguity_conflicting_prices():
    """Multiple prices in a single sentence trigger ambiguity flagging and preserve the sentence."""
    claim = "The petrol costs Rs. 120 in zone A but Rs. 95 in zone B."
    is_ambig, reason = detect_claim_ambiguity(claim)
    assert is_ambig is True
    assert reason is not None
    assert "Multiple conflicting prices" in reason

    # When ambiguous, decompose_compound_claim preserves the original transcript in full
    atoms = decompose_compound_claim(claim)
    assert len(atoms) == 1
    assert atoms[0] == "The petrol costs Rs. 120 in zone A but Rs. 95 in zone B."


def test_detect_claim_ambiguity_contrasting_statements():
    """Contrasting statements with figures trigger ambiguity flagging."""
    claim = "The official price is $10 however unauthorized vendors charged $25."
    is_ambig, reason = detect_claim_ambiguity(claim)
    assert is_ambig is True
    assert "Multiple conflicting prices" in reason or "Contradictory" in reason


def test_unambiguous_claim_not_flagged():
    """A standard factual statement with a single price is not flagged as ambiguous."""
    claim = "The petrol costs Rs. 120 per litre at the local station."
    is_ambig, reason = detect_claim_ambiguity(claim)
    assert is_ambig is False
    assert reason is None


# ─── 4. EPISTEMIC VERDICT TAXONOMY (UNVERIFIED vs MISLEADING) ─────────────────

def test_canonical_verdict_label_distinguishes_unverified_from_misleading():
    """
    _canonical_verdict_label must distinguish UNVERIFIED from MISLEADING:
    - Insufficient/unverified evidence -> 'unverified'
    - Partial/distorted evidence -> 'misleading'
    """
    assert _canonical_verdict_label("unverified") == "unverified"
    assert _canonical_verdict_label("unverifiable") == "unverified"
    assert _canonical_verdict_label("insufficient") == "unverified"
    assert _canonical_verdict_label("inconclusive") == "unverified"
    assert _canonical_verdict_label("ambiguous") == "unverified"
    
    assert _canonical_verdict_label("misleading") == "misleading"
    assert _canonical_verdict_label("partially_supported") == "misleading"
    assert _canonical_verdict_label("distorted") == "misleading"
    assert _canonical_verdict_label("partial") == "misleading"
    
    assert _canonical_verdict_label("supported") == "true"
    assert _canonical_verdict_label("contradicted") == "false"


def test_verdict_label_enum_unverified():
    """VerdictLabel enum correctly contains UNVERIFIED."""
    assert VerdictLabel.UNVERIFIED == "unverified"
    assert VerdictLabel("unverified") == VerdictLabel.UNVERIFIED
    assert VerdictLabel("insufficient") == VerdictLabel.UNVERIFIED


def test_overall_verdict_all_unverified():
    """When all claims are unverified, overall verdict is Unverified, not Misleading."""
    verdicts = [
        {"verdict": {"label": "unverified", "confidence": 0.20}},
        {"verdict": {"label": "unverified", "confidence": 0.20}},
    ]
    res = compute_overall_verdict(verdicts)
    assert res["final_verdict_category"] == "Unverified"
    assert "Unverified" in res["overall_verdict"]
    assert res["verdict_breakdown"]["unverified"] == 2


def test_overall_verdict_mixed_true_and_unverified():
    """When some claims are true and none are false or misleading, category is Likely Genuine."""
    verdicts = [
        {"verdict": {"label": "true", "confidence": 0.85}},
        {"verdict": {"label": "unverified", "confidence": 0.20}},
    ]
    res = compute_overall_verdict(verdicts)
    assert res["final_verdict_category"] == "Likely Genuine"
    assert "Partially Corroborated" in res["overall_verdict"]


def test_overall_verdict_strictly_misleading_when_contradicted_and_supported():
    """Misleading is reserved for mixed/distorted evidence."""
    verdicts = [
        {"verdict": {"label": "true", "confidence": 0.85}},
        {"verdict": {"label": "false", "confidence": 0.90}},
    ]
    res = compute_overall_verdict(verdicts)
    assert res["final_verdict_category"] == "Manipulated"
    assert "Misleading" in res["overall_verdict"]


# ─── 5. METRIC SEPARATION ─────────────────────────────────────────────────────

def test_fact_check_summary_metrics_are_distinct():
    """
    Source relevance, evidence support, source acceptance, verdict confidence,
    and consensus must be calculated and preserved as separate, uncollapsed metrics.
    """
    item1 = ClassifiedEvidenceItem(
        source_url="https://reputable-source-a.org/news/1",
        source_title="Source A Report",
        domain="reputable-source-a.org",
        snippet="Official figures state petrol is 120.",
        relevance_score=0.90,
        credibility_score=0.85,
        stance=EvidenceStance.SUPPORTS,
        is_independent=True,
    )
    item2 = ClassifiedEvidenceItem(
        source_url="https://reputable-source-b.gov/report",
        source_title="Ministry Bulletin",
        domain="reputable-source-b.gov",
        snippet="Ministry data shows price at 120 per unit.",
        relevance_score=0.80,
        credibility_score=0.95,
        stance=EvidenceStance.SUPPORTS,
        is_independent=True,
    )
    rejected = [{"source_url": "https://spammy-site.xyz", "domain": "spammy-site.xyz"}]

    metrics = compute_consensus_and_metrics([item1, item2], rejected_items=rejected)

    # 1. source_relevance: average of accepted items ( (0.90 + 0.80) / 2 = 0.85 )
    assert "source_relevance" in metrics
    assert metrics["source_relevance"] == 0.85

    # 2. evidence_support: support ratio ( 2 / 2 = 1.0 )
    assert "evidence_support" in metrics
    assert metrics["evidence_support"] == 1.0

    # 3. source_acceptance: accepted / total ( 2 / 3 ≈ 0.667 )
    assert "source_acceptance" in metrics
    assert metrics["source_acceptance"] == round(2 / 3, 3)

    # 4. consensus / consensus_score
    assert "consensus_score" in metrics
    assert "consensus" in metrics
    assert metrics["consensus_score"] > 0.0

    # 5. Calibrated confidence is separate
    calibrated_conf = compute_calibrated_confidence("true", [item1, item2], metrics["consensus_score"], 0.80)
    assert 0.0 <= calibrated_conf <= 1.0


def test_fuse_scores_does_not_penalize_unverified_as_false():
    """Unverified claims must maintain baseline score rather than applying false penalty."""
    forensics = {"video_integrity_score": 80.0, "audio_integrity_score": 80.0, "metadata_integrity_score": 80.0}
    osint = {"osint_score": 80.0, "contradiction_count": 0}
    dm = {"dm_score": 80.0}

    claim_unverified = [{"verdict": {"label": "unverified"}}]
    claim_false = [{"verdict": {"label": "false"}}]

    score_unverified = fuse_scores(forensics, osint, dm, claim_unverified)["overall_confidence"]
    score_false = fuse_scores(forensics, osint, dm, claim_false)["overall_confidence"]

    assert score_unverified > score_false, f"Unverified score ({score_unverified}) should be higher than false score ({score_false})"


# ─── 6. ROBUST CLAIM FILTERING & SEARCH FALLBACK INTEGRATION ─────────────────

def test_clean_and_filter_claims_supports_both_dicts_and_strings():
    """clean_and_filter_claims must handle list of strings and list of dicts without AttributeError."""
    raw_claims = [
        "The Earth revolves around the Sun in approximately 365 days.",
        {"claim": "Water boils at 100 degrees Celsius under standard atmospheric pressure.", "context": "Science class"},
        {"text": "The Moon's gravitational pull influences ocean tides.", "context": "Astrophysics"},
    ]
    filtered = clean_and_filter_claims(raw_claims)
    assert len(filtered) == 3
    for c in filtered:
        assert isinstance(c, dict)
        assert "claim" in c
        assert len(c["claim"]) > 10


def test_clean_and_filter_claims_preserves_standard_english_facts():
    """Factual propositions with common English words must not be dropped by aggressive stop word filtering."""
    factual_claim = [{"claim": "This new law will increase the price of all vehicles by ten percent next month."}]
    filtered = clean_and_filter_claims(factual_claim)
    assert len(filtered) == 1
    assert "increase the price of all vehicles" in filtered[0]["claim"]


def test_search_error_fallback_label_is_unverified():
    """In search.py, an error fallback must return label 'unverified' rather than 'misleading'."""
    from pipeline.search import gather_evidence_for_claim
    from unittest.mock import patch

    with patch("pipeline.search._fetch_web_evidence", side_effect=RuntimeError("Search network outage")):
        res = gather_evidence_for_claim("Test claim about economic inflation.", "Test claim about economic inflation.")
        assert res["label"] == "unverified"
        assert res.get("unverified") is True


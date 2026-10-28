"""
data_mining.py — TrueLens Data Mining Analysis Module
=====================================================
Implements pattern mining, anomaly detection, clustering, association rules,
and transparent multi-signal weighting for multimodal fact-checking.

Core Architectural Principles:
  1. Pattern Identification, Not Verdict Declaration:
     Data mining identifies linguistic patterns, topic clusters, statistical
     outliers, and template similarities. It does NOT independently classify
     content as deceptive, fake, or debunked. Claim verdicts are determined
     strictly by verified, claim-specific evidence.
  2. Validated Suspicion Thresholds:
     Continuous suspicion scores [0.0, 1.0] are mapped to standardized severity tiers:
       - 0.00 to 0.20: Low / Minimal Anomaly
       - 0.21 to 0.45: Moderate Anomaly (e.g., 0.38 is strictly moderate, never severe)
       - 0.46 to 0.70: Elevated Anomaly
       - > 0.70:       High Anomaly
  3. Distinction Between Pattern Confidence and Verdict Confidence:
     Pattern confidence reflects how reliably linguistic and structural patterns
     are detected from available sample data. Verdict confidence reflects empirical
     evidence supporting or refuting specific claims.
  4. Actual Computed Data:
     All clusters, outliers, association rules (support, confidence, lift),
     template matches, and scores derive from actual computed statistics.
  5. Transparent Signal Weighting:
     Uncertainty discounts are transparently computed without false claims of
     formal statistical calibration (e.g., Platt scaling or isotonic regression).
"""

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ─── Standardized Suspicion Thresholds ────────────────────────────────────────

THRESHOLD_LOW = 0.20        # 0.00 – 0.20: Minimal / Low Pattern Anomaly
THRESHOLD_MODERATE = 0.45   # 0.21 – 0.45: Moderate Pattern Anomaly (0.38 is strictly moderate)
THRESHOLD_ELEVATED = 0.70   # 0.46 – 0.70: Elevated Pattern Anomaly
                            # > 0.70:      High Pattern Anomaly


def get_suspicion_severity(score: float) -> str:
    """
    Map suspicion score [0.0, 1.0] to a standardized severity tier using validated thresholds.
    Enforces that scores like 0.38 are categorized as 'moderate', never 'severe'.
    """
    score = min(max(float(score), 0.0), 1.0)
    if score <= THRESHOLD_LOW:
        return "low"
    elif score <= THRESHOLD_MODERATE:
        return "moderate"
    elif score <= THRESHOLD_ELEVATED:
        return "elevated"
    else:
        return "high"


# ─── 1. Data Cleaning ─────────────────────────────────────────────────────────

def clean_evidence_items(evidence_list: List[Dict]) -> List[Dict]:
    """Remove duplicates, normalize relevance scores, and filter empty entries."""
    if not evidence_list:
        return []
    seen_urls = set()
    cleaned = []
    for ev in evidence_list:
        url = ev.get("source_url") or ev.get("url") or ""
        snippet = (ev.get("snippet") or ev.get("excerpt") or ev.get("title") or ev.get("domain") or "").strip()
        if not snippet or (url and url in seen_urls):
            continue
        if url:
            seen_urls.add(url)
        rel = float(ev.get("relevance_score", 0.7))
        ev["relevance_score"] = min(max(rel, 0.0), 1.0)
        cleaned.append(ev)
    return cleaned


def normalize_claim_scores(claim_items: List[Dict]) -> List[Dict]:
    """
    Soft-normalize raw confidence scores across claims when sufficient samples exist (N >= 3).
    Preserves original relative order while dampening extreme outliers.
    """
    if not claim_items or len(claim_items) < 3:
        return claim_items
    confidences = [item["verdict"]["confidence"] for item in claim_items if "verdict" in item and "confidence" in item["verdict"]]
    if len(confidences) < 3:
        return claim_items

    avg = sum(confidences) / len(confidences)
    variance = sum((c - avg) ** 2 for c in confidences) / len(confidences)
    std = math.sqrt(variance)
    if std < 1e-4:
        return claim_items

    for item in claim_items:
        if "verdict" in item and "confidence" in item["verdict"]:
            raw = item["verdict"]["confidence"]
            # Soft z-score dampening bounded in [0.25, 0.98]
            normalized = 0.5 + (raw - avg) / (2.5 * std) * 0.25
            item["verdict"]["confidence"] = round(min(max(normalized, 0.25), 0.98), 3)
    return claim_items


# ─── 2. Classification (Pattern Anomaly Level) ────────────────────────────────

MISINFORMATION_KEYWORDS = [
    "secret", "they don't want you to know", "cover up", "banned", "censored",
    "mainstream media won't tell", "wake up", "sheeple", "plandemic", "hoax",
    "fake news", "deep state", "conspiracy", "suppressed", "hidden truth",
    "100% cure", "miracle", "doctors hate", "big pharma", "government hiding",
]

CREDIBILITY_SIGNALS = [
    "study shows", "research found", "scientists say", "according to",
    "official report", "peer reviewed", "published in", "data shows",
    "statistics indicate", "experts agree", "evidence suggests",
]


def classify_content(
    transcript: str,
    claim_items: List[Dict],
    forensics_report: Dict,
    osint_report: Dict,
) -> Dict[str, Any]:
    """
    Compute multi-signal pattern anomaly score and assign a pattern anomaly classification.
    Data mining identifies patterns and statistical anomalies — it does NOT independently
    classify content as deceptive or debunked. Claim verdicts are based on verified evidence.
    """
    transcript_clean = (transcript or "").strip()
    words = re.findall(r'\b\w+\b', transcript_clean.lower())
    word_count = len(words)

    # ── Handle Insufficient Data Gracefully ──
    if not claim_items and word_count < 15:
        return {
            "category": "Insufficient Pattern Data",
            "confidence": 0.20,
            "pattern_confidence": 0.20,
            "suspicion_score": 0.0,
            "suspicion_severity": "low",
            "dm_veto": {"veto": False, "verdict": None, "reason": None, "anomaly_flag": False},
            "signals": {
                "false_claim_ratio": 0.0,
                "true_claim_ratio": 0.0,
                "misinfo_keyword_score": 0.0,
                "credibility_keyword_score": 0.0,
                "forensics_red_flags": 0.0,
                "deepfake_probability": 0.0,
                "osint_contradiction_score": 0.0,
                "recycled_content": 0.0,
            },
        }

    signals = {}

    # Signal 1: Claim verdict distribution from existing verified claims
    verdicts = [item["verdict"]["label"].lower() for item in claim_items if "verdict" in item and "label" in item["verdict"]]
    total_claims = len(verdicts)
    v_counter = Counter(verdicts)

    if total_claims > 0:
        false_ratio = (v_counter.get("false", 0) + v_counter.get("contradicted", 0) + v_counter.get("misleading", 0)) / total_claims
        true_ratio = (v_counter.get("true", 0) + v_counter.get("supported", 0)) / total_claims
    else:
        false_ratio = 0.0
        true_ratio = 0.0

    signals["false_claim_ratio"] = round(false_ratio, 3)
    signals["true_claim_ratio"] = round(true_ratio, 3)

    # Signal 2: Transcript keyword analysis (normalized by text length)
    transcript_lower = transcript_clean.lower()
    misinfo_hits = sum(1 for kw in MISINFORMATION_KEYWORDS if kw in transcript_lower)
    credibility_hits = sum(1 for kw in CREDIBILITY_SIGNALS if kw in transcript_lower)

    # Scale hits based on word count with saturation bounds
    norm_factor = max(word_count / 100.0, 1.0)
    signals["misinfo_keyword_score"] = round(min(misinfo_hits / (3.0 * norm_factor), 1.0), 3)
    signals["credibility_keyword_score"] = round(min(credibility_hits / (3.0 * norm_factor), 1.0), 3)

    # Signal 3: Forensics red flags (from technical stream analysis)
    red_flags = forensics_report.get("red_flag_count", 0) if isinstance(forensics_report, dict) else 0
    signals["forensics_red_flags"] = round(min(red_flags / 5.0, 1.0), 3)

    # Signal 4: Technical synthetic probability
    deepfake_prob = forensics_report.get("deepfake_probability", 0.0) if isinstance(forensics_report, dict) else 0.0
    signals["deepfake_probability"] = round(min(max(float(deepfake_prob), 0.0), 1.0), 3)

    # Signal 5: OSINT contradictions & recycled footage
    osint_contradictions = osint_report.get("contradiction_count", 0) if isinstance(osint_report, dict) else 0
    recycled_content = bool(
        osint_report.get("potential_recycled_content") or osint_report.get("recycled_footage_detected")
    ) if isinstance(osint_report, dict) else False
    signals["osint_contradiction_score"] = round(min(osint_contradictions / 3.0, 1.0), 3)
    signals["recycled_content"] = 1.0 if recycled_content else 0.0

    # ── Weighted Multi-Signal Pattern Suspicion Score ──
    suspicion_score = (
        false_ratio * 0.30
        + signals["misinfo_keyword_score"] * 0.20
        + signals["forensics_red_flags"] * 0.15
        + signals["deepfake_probability"] * 0.15
        + signals["osint_contradiction_score"] * 0.10
        + (0.10 if recycled_content else 0.0)
    )
    credibility_mitigation = (true_ratio * 0.15 + signals["credibility_keyword_score"] * 0.10)
    final_score = min(max(0.0, suspicion_score - credibility_mitigation), 1.0)
    final_score = round(final_score, 3)

    severity = get_suspicion_severity(final_score)

    # ── Pattern Confidence (Distinguished from Verdict Confidence) ──
    # Pattern confidence measures statistical reliability of detected patterns based on sample size:
    sample_size_factor = min((word_count / 150.0) * 0.5 + (total_claims / 4.0) * 0.5, 1.0)
    pattern_confidence = round(min(0.40 + sample_size_factor * 0.50, 0.92), 3)

    # ── Map Suspicion Severity to Descriptive Narrative Category ──
    # Categories describe pattern anomaly levels, NOT unverified claim verdicts.
    if recycled_content:
        category = "Recycled Context Anomaly"
    elif severity == "high":
        category = "High Pattern Anomaly Cluster"
    elif severity == "elevated":
        category = "Elevated Linguistic / Structural Anomaly"
    elif severity == "moderate":
        category = "Moderate Pattern Anomaly"
    elif true_ratio >= 0.50 and final_score <= THRESHOLD_LOW:
        category = "Low Anomaly / Supported Structure"
    elif final_score <= THRESHOLD_LOW:
        category = "Low Pattern Anomaly (Consistent)"
    else:
        category = "Moderate Pattern Anomaly"

    # Data mining identifies patterns and anomalies — it does NOT veto verified claim evidence.
    dm_veto = {
        "veto": False,
        "verdict": None,
        "reason": None,
        "anomaly_flag": severity in ("elevated", "high"),
    }

    return {
        "category": category,
        "confidence": pattern_confidence,
        "pattern_confidence": pattern_confidence,
        "suspicion_score": final_score,
        "suspicion_severity": severity,
        "dm_veto": dm_veto,
        "signals": signals,
    }


# ─── 3. Clustering (Actual TF-IDF Cosine Similarity) ──────────────────────────

def _simple_tfidf_vector(text: str, corpus: List[str]) -> Dict[str, float]:
    """Compute an actual TF-IDF term vector for text within a given corpus."""
    tokens = re.findall(r'\b[a-z]{2,}\b', text.lower())
    if not tokens:
        return {}
    tf = Counter(tokens)
    total_tokens = sum(tf.values())
    tf_norm = {t: c / total_tokens for t, c in tf.items()}

    n_docs = len(corpus)
    df = defaultdict(int)
    for doc in corpus:
        doc_tokens = set(re.findall(r'\b[a-z]{2,}\b', doc.lower()))
        for t in doc_tokens:
            df[t] += 1

    vector = {}
    for term, tf_val in tf_norm.items():
        idf = math.log((n_docs + 1) / (df[term] + 1)) + 1.0
        vector[term] = tf_val * idf
    return vector


def _cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """Compute mathematical cosine similarity between two term vectors."""
    if not v1 or not v2:
        return 0.0
    shared = set(v1.keys()) & set(v2.keys())
    if not shared:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in shared)
    mag1 = math.sqrt(sum(x ** 2 for x in v1.values()))
    mag2 = math.sqrt(sum(x ** 2 for x in v2.values()))
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    return dot / (mag1 * mag2)


def cluster_claims(claim_items: List[Dict], threshold: float = 0.35) -> Dict[str, Any]:
    """
    Cluster claims into thematic groups using actual TF-IDF vector cosine similarity.
    Calculates genuine cluster sizes, representative medoid claims, and dominant verdicts.
    """
    if not claim_items:
        return {"clusters": [], "cluster_count": 0, "largest_cluster_size": 0}

    texts = [item.get("claim", {}).get("normalized_text", "") for item in claim_items]
    vectors = [_simple_tfidf_vector(t, texts) for t in texts]
    n = len(texts)

    clusters: List[List[int]] = []
    assigned = [False] * n

    for i in range(n):
        if assigned[i]:
            continue
        cluster = [i]
        assigned[i] = True
        for j in range(i + 1, n):
            if not assigned[j]:
                sim = _cosine_similarity(vectors[i], vectors[j])
                if sim >= threshold:
                    cluster.append(j)
                    assigned[j] = True
        clusters.append(cluster)

    cluster_summaries = []
    for idx, cluster in enumerate(clusters):
        # Choose medoid claim (highest average similarity within cluster) as representative
        if len(cluster) == 1:
            rep_idx = cluster[0]
        else:
            best_sim = -1.0
            rep_idx = cluster[0]
            for candidate in cluster:
                avg_sim = sum(_cosine_similarity(vectors[candidate], vectors[other]) for other in cluster if other != candidate) / (len(cluster) - 1)
                if avg_sim > best_sim:
                    best_sim = avg_sim
                    rep_idx = candidate

        representative = texts[rep_idx] if rep_idx < len(texts) else ""
        verdicts = [claim_items[k]["verdict"]["label"] for k in cluster if "verdict" in claim_items[k] and "label" in claim_items[k]["verdict"]]
        dominant_verdict = Counter(verdicts).most_common(1)[0][0] if verdicts else "unverifiable"

        cluster_summaries.append({
            "cluster_id": idx + 1,
            "size": len(cluster),
            "representative_claim": representative[:120],
            "dominant_verdict": dominant_verdict,
            "claim_indices": cluster,
        })

    return {
        "clusters": cluster_summaries,
        "cluster_count": len(clusters),
        "largest_cluster_size": max((c["size"] for c in cluster_summaries), default=0),
    }


# ─── 4. Outlier Detection (Actual Z-Scores & Isolation Metrics) ────────────────

def detect_outliers(claim_items: List[Dict]) -> Dict[str, Any]:
    """
    Detect statistical outliers using actual z-scores and empirical distributions:
      - Confidence z-score (|z| >= 2.0)
      - Evidence volume anomalies (ev_count > 2.5 * mean)
      - Verdict isolation (a lone claim contradicting majority consensus)
    Handles small sample sizes gracefully without generating false outliers.
    """
    if not claim_items or len(claim_items) < 2:
        return {
            "outliers": [],
            "outlier_count": 0,
            "anomaly_score": 0.0,
            "avg_confidence": round(claim_items[0]["verdict"].get("confidence", 0.0), 3) if claim_items and "verdict" in claim_items[0] else 0.0,
            "std_confidence": 0.0,
        }

    confidences = [float(item["verdict"]["confidence"]) for item in claim_items if "verdict" in item and "confidence" in item["verdict"]]
    evidence_counts = [len(item["verdict"].get("evidence", [])) for item in claim_items if "verdict" in item]

    if len(confidences) < 2:
        return {"outliers": [], "outlier_count": 0, "anomaly_score": 0.0, "avg_confidence": 0.0, "std_confidence": 0.0}

    n = len(confidences)
    avg_conf = sum(confidences) / n
    variance = sum((c - avg_conf) ** 2 for c in confidences) / n
    std_conf = math.sqrt(variance)

    avg_ev = sum(evidence_counts) / max(len(evidence_counts), 1)

    outliers = []
    all_verdicts = [x["verdict"].get("label", "").lower() for x in claim_items if "verdict" in x]
    majority_verdict = Counter(all_verdicts).most_common(1)[0][0] if all_verdicts else ""

    for i, item in enumerate(claim_items):
        if "verdict" not in item:
            continue
        reasons = []
        conf = float(item["verdict"].get("confidence", avg_conf))
        ev_count = len(item["verdict"].get("evidence", []))

        # 1. Real Z-score check (only when standard deviation is statistically meaningful)
        if std_conf >= 1e-4:
            z_score = abs(conf - avg_conf) / std_conf
            if z_score >= 2.0:
                reasons.append(f"Confidence statistical outlier (|z| = {z_score:.2f} >= 2.0)")

        # 2. Evidence volume anomaly
        if ev_count > 0 and avg_ev > 0 and ev_count >= avg_ev * 2.5 and ev_count >= 5:
            reasons.append(f"Evidence volume anomaly ({ev_count} sources vs {avg_ev:.1f} average)")
        elif ev_count == 0 and conf >= 0.85 and len(claim_items) >= 3 and avg_ev >= 1.5:
            reasons.append("High confidence despite zero supporting evidence sources while peers have evidence")

        # 3. Verdict isolation against established majority
        label = item["verdict"].get("label", "").lower()
        if len(claim_items) >= 4 and label and label != majority_verdict:
            majority_count = Counter(all_verdicts)[majority_verdict]
            if majority_count >= len(claim_items) * 0.75:
                reasons.append(f"Verdict isolation: '{label}' contradicts consensus ({majority_count}/{len(claim_items)} '{majority_verdict}')")

        if reasons:
            severity = "high" if len(reasons) >= 2 or (std_conf >= 1e-4 and abs(conf - avg_conf) / std_conf >= 2.5) else "medium"
            outliers.append({
                "claim_index": i,
                "claim_text": item.get("claim", {}).get("normalized_text", "")[:80],
                "reasons": reasons,
                "anomaly_severity": severity,
            })

    anomaly_score = round(min(len(outliers) / max(len(claim_items), 1), 1.0), 3)

    return {
        "outliers": outliers,
        "outlier_count": len(outliers),
        "anomaly_score": anomaly_score,
        "avg_confidence": round(avg_conf, 3),
        "std_confidence": round(std_conf, 3),
    }


# ─── 5. Association Rules (Actual Apriori Itemset Mining) ─────────────────────

def mine_association_rules(claim_items: List[Dict], min_support: float = 0.20, min_confidence: float = 0.50) -> Dict[str, Any]:
    """
    Mine association rules from actual claim transactions using true statistical formulas:
      - Support(A -> B)    = P(A and B) = count(A and B) / N
      - Confidence(A -> B) = P(B | A)   = count(A and B) / count(A)
      - Lift(A -> B)       = Confidence / P(B) = P(A and B) / (P(A) * P(B))
    No hardcoded, invented, or synthetic rule metrics.
    """
    rules: List[Dict[str, Any]] = []
    if not claim_items or len(claim_items) < 3:
        return {"rules": [], "strong_rules": [], "total_rules": 0}

    # Build genuine transaction itemsets from each claim
    transactions: List[set] = []
    for item in claim_items:
        t = set()
        v = item.get("verdict", {})
        label = v.get("label", "").lower()
        if label:
            t.add(f"verdict={label}")

        conf = float(v.get("confidence", 0.5))
        if conf >= 0.75:
            t.add("confidence=high")
        elif conf <= 0.40:
            t.add("confidence=low")
        else:
            t.add("confidence=moderate")

        ev_list = v.get("evidence", [])
        if not ev_list:
            t.add("evidence=none")
        elif len(ev_list) >= 3:
            t.add("evidence=multiple")
        else:
            t.add("evidence=few")

        # Extract source domains from evidence
        for ev in ev_list:
            domain = ev.get("domain", "")
            if domain:
                clean_dom = domain.split(".")[-2] if "." in domain else domain
                t.add(f"domain={clean_dom.lower()}")
                break  # Primary domain

        transactions.append(t)

    n = len(transactions)
    item_counts = Counter()
    pair_counts = Counter()

    for t in transactions:
        t_list = sorted(list(t))
        for item in t_list:
            item_counts[item] += 1
        for i in range(len(t_list)):
            for j in range(i + 1, len(t_list)):
                pair_counts[(t_list[i], t_list[j])] += 1
                pair_counts[(t_list[j], t_list[i])] += 1

    # Generate directional rules A -> B across distinct namespaces
    for (ant, con), count_ab in pair_counts.items():
        # Avoid redundant intra-attribute rules (e.g. verdict=true -> verdict=true)
        if ant.split("=")[0] == con.split("=")[0]:
            continue

        support = count_ab / n
        if support < min_support:
            continue

        count_a = item_counts[ant]
        count_b = item_counts[con]
        if count_a == 0 or count_b == 0:
            continue

        confidence = count_ab / count_a
        if confidence < min_confidence:
            continue

        prob_b = count_b / n
        lift = confidence / prob_b if prob_b > 0 else 1.0

        rules.append({
            "antecedent": ant,
            "consequent": con,
            "support": round(support, 3),
            "confidence": round(confidence, 3),
            "lift": round(lift, 3),
        })

    # Sort rules by confidence descending, then lift
    rules.sort(key=lambda r: (r["confidence"], r["lift"]), reverse=True)
    strong_rules = [r for r in rules if r["confidence"] >= 0.65 and r["lift"] > 1.05]

    return {
        "rules": rules,
        "strong_rules": strong_rules,
        "total_rules": len(rules),
    }


# ─── 6. Pattern Mining (Actual Linguistic Indicators) ─────────────────────────

def mine_patterns(transcript: str, claim_items: List[Dict]) -> Dict[str, Any]:
    """
    Detect linguistic and structural patterns with validated severity thresholds:
      - Emotional Intensifiers (sensationalism markers)
      - Hedging Language (speculative sourcing)
      - Absolute / Universal Claims
      - Empirical False Claim Concentration
    Severity requires genuine density relative to document length.
    """
    patterns_found = []
    text_clean = (transcript or "").strip()
    words = re.findall(r'\b\w+\b', text_clean.lower())
    total_words = len(words)

    if total_words > 0:
        text_lower = text_clean.lower()

        # 1. Emotional intensifiers
        emotional_words = [
            "shocking", "devastating", "unbelievable", "outrageous",
            "explosive", "bombshell", "urgent", "danger", "catastrophic", "mindblowing"
        ]
        emotion_hits = [w for w in emotional_words if re.search(r'\b' + re.escape(w) + r'\b', text_lower)]
        if emotion_hits:
            # Severity based on hit count and relative density
            is_dense = (len(emotion_hits) / max(total_words, 1)) >= 0.02
            severity = "high" if len(emotion_hits) >= 4 and is_dense else "medium" if len(emotion_hits) >= 2 else "low"
            patterns_found.append({
                "pattern": "Emotional Intensifiers",
                "type": "linguistic",
                "indicators": emotion_hits[:5],
                "severity": severity,
                "description": f"{len(emotion_hits)} sensationalist marker(s) detected — indicates potential manufactured urgency.",
            })

        # 2. Hedging language
        hedging_words = [
            "allegedly", "reportedly", "sources say", "rumored", "unconfirmed",
            "some believe", "it is said", "i heard", "purportedly"
        ]
        hedge_hits = [w for w in hedging_words if w in text_lower]
        if hedge_hits:
            patterns_found.append({
                "pattern": "Hedging Language",
                "type": "linguistic",
                "indicators": hedge_hits[:5],
                "severity": "medium" if len(hedge_hits) >= 3 else "low",
                "description": f"{len(hedge_hits)} speculative phrase(s) found — claims rely on indirect or unconfirmed sourcing.",
            })

        # 3. Absolute assertions
        absolute_phrases = [
            "100% cure", "guaranteed", "proven fact", "nobody talks about",
            "everyone knows", "never fails", "undeniable proof", "irrefutable"
        ]
        abs_hits = [w for w in absolute_phrases if w in text_lower]
        if abs_hits:
            patterns_found.append({
                "pattern": "Absolute Assertions",
                "type": "factual",
                "indicators": abs_hits[:5],
                "severity": "medium" if len(abs_hits) >= 2 else "low",
                "description": f"{len(abs_hits)} universal assertion(s) detected — categorical claims often signal overstatement.",
            })

    # 4. Verified False Claims concentration
    false_claims = [
        item.get("claim", {}).get("normalized_text", "")[:60]
        for item in claim_items
        if item.get("verdict", {}).get("label", "").lower() in ("false", "contradicted")
    ]
    if len(false_claims) >= 2:
        patterns_found.append({
            "pattern": "Multiple Debunked Claims",
            "type": "credibility",
            "indicators": false_claims[:3],
            "severity": "high",
            "description": f"{len(false_claims)} factual claims independently refuted by evidence — clustered misinformation pattern.",
        })

    high_sev = sum(1 for p in patterns_found if p["severity"] == "high")
    risk_score = round(min(len(patterns_found) / 4.0, 1.0), 3)

    return {
        "patterns": patterns_found,
        "pattern_count": len(patterns_found),
        "high_severity_patterns": high_sev,
        "linguistic_risk_score": risk_score,
    }


# ─── 7. Similarity Analysis (Actual Token Jaccard Matching) ───────────────────

KNOWN_MISINFO_TEMPLATES = [
    "this cure was suppressed by doctors",
    "the government is hiding this secret",
    "you won't see this in mainstream media",
    "they are poisoning us with chemicals",
    "this video will be deleted soon share",
    "wake up sheeple the truth exposed",
    "what they don't want you to know about",
    "miracle cure suppressed by big pharma",
]


def similarity_analysis(transcript: str, claim_items: List[Dict]) -> Dict[str, Any]:
    """
    Fuzzy-match against known misinformation rhetoric templates using actual token Jaccard similarity:
      Jaccard(A, B) = |A ∩ B| / |A ∪ B|
    Requires genuine overlap (Jaccard >= 0.25) or full verbatim phrase match.
    """
    transcript_clean = (transcript or "").strip().lower()
    transcript_tokens = set(re.findall(r'\b[a-z]{3,}\b', transcript_clean))
    matches = []

    if transcript_tokens:
        for template in KNOWN_MISINFO_TEMPLATES:
            template_tokens = set(re.findall(r'\b[a-z]{3,}\b', template.lower()))
            intersection = transcript_tokens & template_tokens
            union = transcript_tokens | template_tokens
            jaccard = len(intersection) / len(union) if union else 0.0

            exact_match = template.lower() in transcript_clean

            # Only accept genuine semantic overlap (Jaccard >= 0.25) or exact phrase match
            if exact_match or jaccard >= 0.25:
                sim_score = 1.0 if exact_match else round(jaccard, 3)
                matches.append({
                    "template": template,
                    "similarity_score": sim_score,
                    "exact_match": exact_match,
                    "match_type": "exact" if exact_match else "fuzzy",
                })

    # Also check individual claim texts
    claim_matches = []
    for item in claim_items:
        claim_text = item.get("claim", {}).get("normalized_text", "").lower()
        c_tokens = set(re.findall(r'\b[a-z]{3,}\b', claim_text))
        for template in KNOWN_MISINFO_TEMPLATES:
            t_tokens = set(re.findall(r'\b[a-z]{3,}\b', template.lower()))
            overlap = len(c_tokens & t_tokens)
            if overlap >= 3 or template in claim_text:
                claim_matches.append({
                    "claim": claim_text[:80],
                    "matching_template": template,
                })
                break

    max_sim = max((m["similarity_score"] for m in matches), default=0.0)

    return {
        "template_matches": matches,
        "claim_pattern_matches": claim_matches[:5],
        "total_matches": len(matches),
        "max_similarity": round(max_sim, 3),
        "misinfo_pattern_score": round(min(len(matches) / 2.0, 1.0), 3),
    }


# ─── Master DM Orchestrator ───────────────────────────────────────────────────

def run_data_mining_pipeline(
    transcript: str,
    claim_items: List[Dict],
    forensics_report: Dict,
    osint_report: Dict,
) -> Dict[str, Any]:
    """
    Run the complete TrueLens Data Mining pipeline.
    Identifies patterns, clusters, outliers, and association rules.
    Applies transparent multi-signal uncertainty weighting to claim confidences.
    Does NOT independently classify content as deceptive or debunked.
    """
    forensics_report = forensics_report or {}
    osint_report = osint_report or {}
    claim_items = claim_items or []

    # 1. Clean evidence items
    for item in claim_items:
        if "verdict" in item and "evidence" in item["verdict"]:
            item["verdict"]["evidence"] = clean_evidence_items(item["verdict"]["evidence"])
    claim_items = normalize_claim_scores(claim_items)

    # 2. Classification of pattern anomaly level
    classification = classify_content(transcript, claim_items, forensics_report, osint_report)

    # 3. Topic clustering
    clustering = cluster_claims(claim_items)

    # 4. Outlier detection
    outliers = detect_outliers(claim_items)

    # 5. Association rules
    associations = mine_association_rules(claim_items)

    # 6. Linguistic & thematic pattern mining
    patterns = mine_patterns(transcript, claim_items)

    # 7. Rhetoric template similarity analysis
    similarity = similarity_analysis(transcript, claim_items)

    # ── 8. Transparent Multi-Signal Weighting (Uncertainty Adjustment) ──
    # Transparently reduces claim confidence when structural or linguistic anomalies are present.
    # Note: This is deterministic multi-signal weighting, NOT formal statistical calibration.
    signal_weighted_count = 0
    outlier_indices = {o["claim_index"]: o for o in outliers.get("outliers", [])}
    template_claims = {m.get("claim", "").lower() for m in similarity.get("claim_pattern_matches", [])}

    for idx, item in enumerate(claim_items):
        if "verdict" not in item:
            continue
        v = item["verdict"]
        conf = float(v.get("confidence", 0.70))
        c_text = item.get("claim", {}).get("normalized_text", "").lower()
        penalty = 0.0

        # Penalty 1: Rhetoric template match discount
        if any(t in c_text for t in template_claims) or similarity.get("misinfo_pattern_score", 0.0) >= 0.5:
            penalty += 0.15

        # Penalty 2: Outlier isolation discount
        if idx in outlier_indices:
            out_info = outlier_indices[idx]
            is_high = out_info.get("anomaly_severity") == "high"
            penalty += 0.20 if is_high else 0.10
            v["outlier_flag"] = True
            v["outlier_reasons"] = out_info.get("reasons", [])

        # Penalty 3: Sensationalism discount on unverified claims
        if patterns.get("high_severity_patterns", 0) > 0 and v.get("label", "").lower() in ("unverified", "unverifiable"):
            penalty += 0.10

        if penalty > 0:
            new_conf = max(0.20, min(0.98, round(conf * (1.0 - penalty), 3)))
            v["confidence"] = new_conf
            v["dm_calibrated"] = True  # Preserved for backward compatibility
            v["signal_weighting_applied"] = True
            v["uncertainty_penalty"] = round(penalty, 2)
            signal_weighted_count += 1

    # ── 9. Compute Overall Data Mining Score (0–100) ──
    suspicion = classification["suspicion_score"]
    misinfo_pat = similarity["misinfo_pattern_score"]
    anomaly = outliers["anomaly_score"]
    high_sev_patterns = patterns["high_severity_patterns"]

    dm_risk = (
        suspicion * 0.35
        + misinfo_pat * 0.25
        + anomaly * 0.20
        + min(high_sev_patterns / 3.0, 1.0) * 0.20
    )
    dm_score = round(max(15.0, min(95.0, (1.0 - dm_risk) * 100)), 1)

    # ── 10. Summary Generation with Contextual Warning Explanation ──
    pattern_cnt = patterns["pattern_count"]
    cluster_cnt = clustering["cluster_count"]
    outlier_cnt = outliers["outlier_count"]

    if pattern_cnt == 0 and outlier_cnt == 0 and similarity.get("total_matches", 0) == 0:
        # Check if external systems (Forensics / OSINT / Claim Veracity) hold warnings
        external_reasons = []
        if forensics_report.get("red_flag_count", 0) > 0 or forensics_report.get("deepfake_probability", 0) >= 0.5:
            external_reasons.append("technical media stream forensics anomalies")
        if osint_report.get("contradiction_count", 0) > 0 or osint_report.get("recycled_footage_detected"):
            external_reasons.append("external OSINT corroboration contradictions")
        false_cnt = sum(1 for item in claim_items if item.get("verdict", {}).get("label", "").lower() in ("false", "contradicted"))
        if false_cnt > 0:
            external_reasons.append(f"{false_cnt} verified false claim(s) refuted by evidence")

        if external_reasons:
            explanation = (
                f"No suspicious linguistic or structural data mining patterns detected. "
                f"Any warnings for this content stem from independent evidence sources: {', '.join(external_reasons)}."
            )
        else:
            explanation = "No suspicious data mining patterns or anomalies detected. Content structure is consistent with standard organic discourse."
    else:
        explanation = (
            f"Data Mining Analysis: {cluster_cnt} claim cluster(s), {outlier_cnt} statistical outlier(s), "
            f"{pattern_cnt} linguistic pattern(s), and {similarity.get('total_matches', 0)} rhetoric template match(es) computed. "
            f"Pattern Anomaly Level: {classification['category']} (pattern confidence: {int(classification['confidence'] * 100)}%, "
            f"suspicion score: {int(classification['suspicion_score'] * 100)}% [{classification['suspicion_severity']}]). "
            f"{signal_weighted_count} claim(s) adjusted via transparent multi-signal uncertainty weighting."
        )

    return {
        "dm_score": dm_score,
        "classification": classification,
        "clustering": clustering,
        "outlier_detection": outliers,
        "association_rules": associations,
        "pattern_mining": patterns,
        "similarity_analysis": similarity,
        "dm_veto": classification.get("dm_veto", {"veto": False}),
        "calibrated_claims_count": signal_weighted_count,
        "signal_weighted_claims_count": signal_weighted_count,
        "summary": explanation,
    }

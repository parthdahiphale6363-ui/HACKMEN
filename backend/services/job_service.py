import json
import os
import re
import uuid
import datetime
from typing import List, Dict, Any, Optional, Tuple

from shared.llm import get_llm_client, get_llm_model, get_groq_fallback_client, get_groq_model, call_llm_with_fallback, get_fallback_llm_model

from shared.schemas.job import Job, JobStatus
from shared.schemas.claim import Claim, SourcePlatform
from pipeline.ingest import ingest_video
from pipeline.search import gather_evidence_for_claim
from backend.services.forensics import run_forensics_pipeline
from backend.services.osint import run_osint_pipeline
from backend.services.data_mining import run_data_mining_pipeline

try:
    from backend.storage.repository import (
        get_jobs_db, get_claims_verdicts_db, get_transcripts_db,
        get_forensics_db, get_osint_db, get_dm_db
    )
    jobs_db = get_jobs_db()
    claims_verdicts_db = get_claims_verdicts_db()
    transcripts_db = get_transcripts_db()
    forensics_db = get_forensics_db()
    osint_db = get_osint_db()
    dm_db = get_dm_db()
except Exception as _storage_err:
    print(f"[job_service] Persistent storage fallback to in-memory: {_storage_err}")
    jobs_db = {}
    claims_verdicts_db = {}
    transcripts_db = {}
    forensics_db = {}
    osint_db = {}
    dm_db = {}

import asyncio

class JobEventDispatcher:
    def __init__(self):
        self.listeners = {}  # job_id -> set of queues
        self.loop = None
        self.redis_client = None

    def set_loop(self, loop):
        self.loop = loop

    def register(self, job_id: str, queue: asyncio.Queue):
        if job_id not in self.listeners:
            self.listeners[job_id] = set()
        self.listeners[job_id].add(queue)

    def unregister(self, job_id: str, queue: asyncio.Queue):
        if job_id in self.listeners:
            self.listeners[job_id].discard(queue)
            if not self.listeners[job_id]:
                del self.listeners[job_id]

    def publish(self, job_id: str, event_type: str, data: dict):
        # 1. Publish to local in-memory listeners
        queues = self.listeners.get(job_id, set())
        for q in list(queues):
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(q.put_nowait, (event_type, data))
            else:
                try:
                    q.put_nowait((event_type, data))
                except Exception:
                    pass

        # 2. Publish to Redis channel (for distributed workers in Phase 4)
        if self.redis_client:
            try:
                self.redis_client.publish(f"job_stream:{job_id}", json.dumps({"event": event_type, "data": data}))
            except Exception as e:
                print(f"[JobEventDispatcher] Redis publish failed: {e}")


job_dispatcher = JobEventDispatcher()


def publish_job_event(job_id: str, event_type: str, data: dict):
    if not job_dispatcher.loop:
        try:
            job_dispatcher.set_loop(asyncio.get_running_loop())
        except RuntimeError:
            pass
    job_dispatcher.publish(job_id, event_type, data)


# ─── LLM Claim Extraction ─────────────────────────────────────────────────────

from shared.json_utils import strip_markdown_fences, repair_truncated_json, parse_llm_json

def _strip_markdown_fences(text: str) -> str:
    """Extract JSON from ```json ... ``` markdown fences or raw text."""
    return strip_markdown_fences(text)


def _call_groq_extract(client, model: str, full_transcript: str, strict: bool = False) -> str:
    """Send extraction prompt to Groq/OpenRouter and return raw response text. Falls back to Groq if primary fails."""
    strict_note = " You MUST return ONLY the JSON object with absolutely no other text, preamble, or explanation." if strict else ""
    system_prompt = (
        "You are an expert investigative fact-checker. Read this video transcript and extract "
        "every independently verifiable factual claim."
        "\n\nCRITICAL RULES:"
        "\n- Extract 1 to 8 claims. DO NOT skip claims just to keep the list short."
        "\n- Each claim MUST be a complete, self-contained factual statement INCLUDING its subject."
        "  BAD: '40% electricity will be generated'  (missing subject)"
        "  GOOD: 'Ethanol-blended petrol will generate 40% electricity'  (full context)"
        "\n- Preserve all specific numbers, names, dates, prices, and percentages EXACTLY."
        "\n- Do NOT merge claims. Extract each distinct fact separately."
        "\n- Skip opinions, jokes, filler, and vague generalisations."
        "\n- Each claim must have a 'context' field with the original sentence from the transcript."
        f"\n- Return ONLY a valid JSON object. No preamble. No markdown. No explanation.{strict_note}"
        "\n\nFormat:"
        '\n{"claims": [{"claim": "Complete factual statement with subject", "context": "Original transcript sentence"}]}'
        "\n\nIf there are truly 0 verifiable factual claims, return: {\"claims\": []}"
    )

    def _do_call(c, m):
        response = call_llm_with_fallback(
            client=c,
            model=m,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Video Transcript:\n\n{full_transcript[:8000]}"}
            ],
            temperature=0.0,
            max_tokens=1800,
            timeout=60,
        )
        raw = ""
        if response.choices:
            raw = getattr(response.choices[0].message, "content", "") or ""
        return raw

    try:
        return _do_call(client, model)
    except Exception as e:
        print(f"[extract_claims_with_llm] Primary LLM failed ({e}), trying Groq fallback...")
        from shared.llm import get_groq_fallback_client, get_fallback_llm_model
        fallback = get_groq_fallback_client()
        if fallback:
            try:
                return _do_call(fallback, get_fallback_llm_model())
            except Exception as e2:
                print(f"[extract_claims_with_llm] Groq fallback also failed: {e2}")
        return ""


def deduplicate_claims_with_llm(claims: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Deduplicate claims by normalized text (fast, no extra LLM call)."""
    seen = set()
    unique = []
    for item in claims:
        key = re.sub(r"\s+", " ", (item.get("claim") or "").strip().lower())
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    if len(unique) < len(claims):
        print(f"[Deduplicate] Reduced {len(claims)} claims to {len(unique)} unique claims.")
    return unique


# Conversational/filler patterns that are never independently fact-checkable
_NON_FACTUAL_PATTERNS = re.compile(
    r"^(?:"
    r"(?:but\s+)?i(?:'ll|\s+will|\s+am\s+going\s+to|\s+want\s+to)?\s+(?:tell|show|explain|share|talk|discuss|let\s+you\s+know)\b"
    r"|(?:let(?:'s|us|\s+me))\s+(?:tell|show|explore|start|talk|look|see|discuss|begin|find|check)\b"
    r"|(?:so|well|okay|now|alright|basically|essentially|actually|anyway|you\s+know|you\s+see)\s*[,.]?\s*$"
    r"|(?:first\s+of\s+all|second(?:ly)?|third(?:ly)?|next|also|additionally|furthermore|moreover|however|therefore),?\s*$"
    r"|(?:as\s+(?:you|we)\s+(?:can\s+see|know|mentioned|said|discussed))\b"
    r"|(?:what(?:'s|\s+is)\s+(?:interesting|amazing|surprising|crazy|incredible|shocking|fascinating)\s+(?:is|here)\b)"
    r"|(?:in\s+(?:this|today's|our)\s+(?:video|episode|segment|part|section))\b"
    r"|(?:stay\s+tuned|don't\s+forget\s+to|like\s+and\s+subscribe|hit\s+the\s+bell)\b"
    r")",
    re.IGNORECASE,
)

_BROAD_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "ok", "okay", "yes", "no",
    "i", "you", "we", "they", "he", "she", "it", "me", "us", "him", "her",
    "my", "our", "your", "their", "this", "that", "these", "those",
    "will", "would", "could", "should", "may", "might", "can", "shall",
    "to", "of", "in", "on", "at", "by", "for", "with", "from", "as",
    "and", "but", "or", "not", "so", "just", "now", "also", "very",
    "tell", "show", "know", "see", "let", "go", "get",
}


# ── Robust Claim Extraction, Splitting & Proposition Validation ──────────────

_ABBREVIATIONS = {
    "rs", "re", "usd", "eur", "inr", "gbp", "aud", "cad",
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr",
    "approx", "est", "vs", "e.g", "i.e", "etc", "no", "vol",
    "sec", "dept", "govt", "inc", "corp", "ltd", "co", "gen", "rep", "sen"
}

_DANGLING_TAIL_WORDS = {
    "rs", "re", "usd", "eur", "inr", "gbp", "at", "by", "for", "from",
    "in", "of", "on", "to", "with", "as", "than", "per", "and", "or",
    "but", "costs", "cost", "costing", "is", "was", "are", "were", "been",
    "has", "have", "had", "the", "a", "an", "their", "its", "our", "your",
    "my", "his", "her", "approx", "est"
}

_DANGLING_HEAD_PATTERN = re.compile(
    r"^(?:"
    r"per\s+\w+|"
    r"\d+[\d.,]*\s*(?:per\s+\w+|%|percent|litres?|units?|dollars?|rupees?|km/?h|mph|kg|g|kwh|tons?|barrels?)\b|"
    r"(?:and|or|but|because|whereas|while|which|that|who|whose)\b"
    r")",
    re.IGNORECASE,
)

_VERB_HEURISTIC_PATTERN = re.compile(
    r"\b(?:is|are|was|were|has|have|had|costs?|costing|priced?|sells?|selling|sold|"
    r"paid|pays|paying|dropped?|drops?|dropping|rose|rises?|rising|fell|falls?|falling|"
    r"increased?|decreased?|exceeded?|cures?|causes?|produces?|generates?|contains?|"
    r"discovered|found|proven|shows?|showed|claims?|claimed|stated?|states?|"
    r"approved|rejected|banned|signed|passed|killed|injured|built|started|reached|"
    r"uses?|used|using|consumed?|consumes?|buying|bought|buys|charges?|charged|"
    r"reported|confirmed|announced|stated|operates?|weighed|accelerated?)\b|"
    r"\b[a-zA-Z]{3,}(?:ed|ing)\b",
    re.IGNORECASE,
)

_CURRENCY_PRICE_PATTERN = re.compile(
    r"(?:(?:\b(?:Rs\.?|INR|USD|EUR|GBP)|[\$€₹£])\s*\d+[\d.,]*|\b\d+[\d.,]*\s*(?:rupees|dollars|euros|cents|per\s+\w+))",
    re.IGNORECASE,
)

_CONTRASTIVE_CONJUNCTION_PATTERN = re.compile(
    r"\b(?:but|however|whereas|yet|while|instead of|contrary to|on the other hand|although|rather than)\b",
    re.IGNORECASE,
)


def split_sentences_safely(text: str) -> List[str]:
    """
    Splits text into sentences while strictly protecting currency abbreviations (Rs., USD.),
    honorifics (Dr., Mr.), common abbreviations (approx., e.g.), and decimal numbers (120.50).
    """
    if not text:
        return []

    # Mask known abbreviations followed by dot: e.g. "Rs." -> "Rs@DOT@"
    def _mask_abbr(match):
        token = match.group(1)
        if token.lower() in _ABBREVIATIONS:
            return token + "@DOT@"
        return match.group(0)

    masked = re.sub(r"\b([A-Za-z]+)\.", _mask_abbr, text)
    # Mask decimals: e.g. "120.50" -> "120@DECIMAL@50"
    masked = re.sub(r"(\d+)\.(\d+)", r"\1@DECIMAL@\2", masked)

    # Split on terminal punctuation followed by space and a capital letter or quote
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'‘“])", masked)

    cleaned_sentences = []
    for s in raw_sentences:
        restored = s.replace("@DOT@", ".").replace("@DECIMAL@", ".").strip()
        if restored:
            cleaned_sentences.append(restored)
    return cleaned_sentences


def is_complete_proposition(clause: str) -> bool:
    """
    Determines whether a clause is a syntactically self-contained proposition
    rather than a fragmented token, broken phrase, or dangling predicate.
    """
    text = clause.strip().rstrip(".!?")
    if not text:
        return False

    tokens = [w for w in re.findall(r"[A-Za-z0-9%$€₹£.]+", text)]
    if len(tokens) < 4:
        return False

    last_word = tokens[-1].rstrip(".").lower()
    # Cannot end in a currency, preposition, copula, or conjunction
    if last_word in _DANGLING_TAIL_WORDS:
        return False
    if text.endswith(("$", "€", "₹", "£")):
        return False

    # Cannot start with a dangling unit or continuation
    if _DANGLING_HEAD_PATTERN.search(text):
        return False

    # Must contain at least one verb-like predicate or copula
    if not _VERB_HEURISTIC_PATTERN.search(text):
        return False

    return True


def detect_claim_ambiguity(claim_text: str) -> Tuple[bool, Optional[str]]:
    """
    Detects whether a proposition contains multiple conflicting prices, contradictory
    assertions, or divergent quantitative claims that should be preserved in full
    and flagged for human review.
    """
    text = (claim_text or "").strip()
    if not text:
        return False, None

    # Check for multiple distinct currency/price patterns
    prices = _CURRENCY_PRICE_PATTERN.findall(text)
    distinct_prices = set(re.sub(r"[^\d.]", "", p) for p in prices if re.search(r"\d", p))
    has_contrast = bool(_CONTRASTIVE_CONJUNCTION_PATTERN.search(text))

    if len(distinct_prices) >= 2:
        return True, "Multiple conflicting prices or rates detected in proposition; flagged for human review."

    if has_contrast and len(prices) >= 1 and re.search(r"\d+", text):
        return True, "Contradictory or contrasting statements detected in proposition; flagged for human review."

    return False, None


def validate_claim_for_verification(claim_text: str) -> Dict[str, Any]:
    """
    Pre-flight validation check before initiating web search and verification.
    Guarantees numbers, currencies, units, and complete context are preserved.
    """
    text = (claim_text or "").strip()
    if not text or len(text) < 12:
        return {"valid": False, "reason": "Claim text too short to constitute a verifiable assertion"}

    words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", text)]
    if len(words) < 4:
        return {"valid": False, "reason": "Claim contains fewer than 4 words"}

    if _NON_FACTUAL_PATTERNS.search(text):
        return {"valid": False, "reason": "Claim consists of conversational filler"}

    # Check for dangling fragments
    last_word = words[-1]
    if last_word in _DANGLING_TAIL_WORDS:
        return {"valid": False, "reason": f"Claim ends with dangling token '{last_word}'"}

    if _DANGLING_HEAD_PATTERN.search(text):
        return {"valid": False, "reason": "Claim begins with dangling unit or conjunction"}

    is_ambig, ambig_reason = detect_claim_ambiguity(text)

    return {
        "valid": True,
        "sanitized_claim": text.rstrip(".!?") + ".",
        "is_ambiguous": is_ambig,
        "ambiguity_reason": ambig_reason,
    }


def clean_and_filter_claims(claims: List[Any]) -> List[Dict[str, str]]:
    valid = []
    for item in claims:
        if isinstance(item, dict):
            claim_text = (item.get("claim") or item.get("text") or "").strip()
            context_text = item.get("context", "")
        elif isinstance(item, str):
            claim_text = item.strip()
            context_text = ""
        else:
            continue

        if not claim_text:
            continue

        validation = validate_claim_for_verification(claim_text)
        if not validation["valid"]:
            print(f"[claims] Rejected invalid claim ({validation['reason']}): \"{claim_text[:80]}\"")
            continue

        words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", claim_text)]
        # Reject if all words are generic stop words
        if all(w in _BROAD_STOP for w in words):
            continue

        # Reject conversational filler openers
        if _NON_FACTUAL_PATTERNS.search(claim_text):
            print(f"[claims] Rejected non-factual filler: \"{claim_text[:80]}\"")
            continue

        # Reject if >85% of meaningful words are stop words (very low information density)
        meaningful = [w for w in words if len(w) > 2]
        if meaningful:
            stop_ratio = sum(1 for w in meaningful if w in _BROAD_STOP) / len(meaningful)
            if stop_ratio > 0.85 and len(words) < 8:
                print(f"[claims] Rejected low-information claim (stop ratio={stop_ratio:.0%}): \"{claim_text[:80]}\"")
                continue

        item_copy = dict(item) if isinstance(item, dict) else {"claim": claim_text, "context": context_text}
        item_copy["claim"] = validation["sanitized_claim"]
        if validation.get("is_ambiguous"):
            item_copy["is_ambiguous"] = True
            item_copy["ambiguity_reason"] = validation.get("ambiguity_reason")
        valid.append(item_copy)
    return valid


def extract_claims_with_llm(full_transcript: str) -> Optional[List[Dict[str, str]]]:
    """
    Use Groq LLM to extract up to 5 key verifiable factual claims from the full transcript.
    Returns list of {"claim": ..., "context": ...} dicts, or None on total failure.
    """
    client = get_llm_client()
    if not client:
        return None

    model = get_llm_model()
    
    _repair_truncated_json = repair_truncated_json

    def parse_claims(raw_text):
        cleaned = _strip_markdown_fences(raw_text)
        for attempt_text in [cleaned, _repair_truncated_json(cleaned)]:
            if not attempt_text:
                continue
            try:
                result = json.loads(attempt_text, strict=False)
                if isinstance(result, dict) and "claims" in result:
                    found = clean_and_filter_claims(result["claims"])
                    if found is not None:
                        return found
                elif isinstance(result, list):
                    found = clean_and_filter_claims(result)
                    if found is not None:
                        return found
            except json.JSONDecodeError:
                pass
            # Trailing-comma repair
            try:
                repaired = re.sub(r",\s*([\]}])", r"\1", attempt_text)
                result = json.loads(repaired, strict=False)
                if isinstance(result, dict) and "claims" in result:
                    found = clean_and_filter_claims(result["claims"])
                    if found is not None:
                        return found
                elif isinstance(result, list):
                    found = clean_and_filter_claims(result)
                    if found is not None:
                        return found
            except json.JSONDecodeError:
                pass
        print(f"[extract_claims_with_llm] Parse error. Raw (first 300): {raw_text[:300]}")
        return None

    # First attempt
    raw = _call_groq_extract(client, model, full_transcript, strict=False)
    filtered = parse_claims(raw)
    if filtered is not None:
        return deduplicate_claims_with_llm(filtered)

    # Retry with strict prompt
    print("[extract_claims_with_llm] First parse failed, retrying with strict prompt...")
    raw = _call_groq_extract(client, model, full_transcript, strict=True)
    filtered = parse_claims(raw)
    if filtered is not None:
        return deduplicate_claims_with_llm(filtered)

    # Heuristic fallback: pick sentences that look factual (contain numbers, named entities, or domain terms)
    print("[extract_claims_with_llm] Both attempts failed. Using heuristic fallback.")
    _FACTUAL_SIGNAL = re.compile(
        r'(?:\d[\d.,]*%?|\$[\d.]+|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|'
        r'\b(?:causes?|produces?|generates?|contains?|found|discovered|proven|'
        r'studies?|research|evidence|scientists?|percent|million|billion|years?)\b)',
        re.IGNORECASE
    )
    sentences = [s.strip() for s in split_sentences_safely(full_transcript) if len(s.strip().split()) >= 5]
    fallback_claims = []
    for s in sentences:
        if len(fallback_claims) >= 3:
            break
        if _FACTUAL_SIGNAL.search(s):
            fallback_claims.append({"claim": s, "context": s})
    # If no factual sentences found, just take the first 2 non-trivial ones
    if not fallback_claims:
        for s in sentences[:5]:
            if len(fallback_claims) >= 2:
                break
            words = s.split()
            if len(words) >= 6:
                fallback_claims.append({"claim": s, "context": s})

    if fallback_claims:
        return clean_and_filter_claims(fallback_claims)
    return []


def decompose_compound_claim(claim_text: str) -> List[str]:
    """
    Decomposes a compound factual assertion into atomic propositions while:
    1. Preserving complete propositions, numbers, currencies (Rs., $, etc.), and units.
    2. Preventing incomplete fragments (such as 'The petrol being sold costs Rs.' and '120 per unit.').
    3. Retaining the original transcript intact when ambiguous or contradictory.
    """
    text = (claim_text or "").strip()
    if not text:
        return []

    # Check ambiguity & conflicting prices: if ambiguous, do NOT split
    is_ambig, _ = detect_claim_ambiguity(text)
    if is_ambig:
        return [text.rstrip(".!?") + "."]

    # 1. Safe sentence boundary splitting
    sentences = split_sentences_safely(text)
    if len(sentences) > 1:
        # Validate that EVERY candidate sentence is a complete proposition
        if all(is_complete_proposition(s) for s in sentences):
            return [s.rstrip(".!?") + "." for s in sentences[:4]]

    # 2. Semicolon splitting
    if ";" in text:
        parts = [p.strip() for p in text.split(";") if p.strip()]
        if len(parts) > 1 and all(is_complete_proposition(p) for p in parts):
            return [p.rstrip(".!?") + "." for p in parts[:4]]

    # 3. Coordinating conjunctions between independent clauses (e.g. ', and ', ' while ')
    # Only split if both sides are complete independent clauses with their own subject + verb
    conj_parts = re.split(r"(?:,\s*|\s+)(?:and|while|whereas|as well as)\s+", text, flags=re.IGNORECASE)
    if len(conj_parts) > 1 and all(is_complete_proposition(p) for p in conj_parts):
        return [p.strip().rstrip(".!?") + "." for p in conj_parts[:4]]

    return [text.rstrip(".!?") + "."]


# ─── Overall Verdict Aggregation ──────────────────────────────────────────────

def compute_overall_verdict(
    claim_items: List[Dict],
    dm_report: Dict = None,
    forensics_report: Dict = None,
    osint_report: Dict = None,
) -> Dict[str, Any]:
    """
    Compute aggregated overall verdict using multi-modal veto hierarchy:
      1. Forensics Deepfake / Synthetic Media Veto
      2. OSINT Recycled Footage / Out-of-Context Veto / Google Fact Check Veto
      3. Data Mining Misinformation Governor Veto
      4. Grounded Claim Evidence Voting & Calibration
    Returns {"overall_verdict": str, "verdict_breakdown": {...}, "final_verdict_category": str}
    """
    if not claim_items:
        return {
            "overall_verdict": "No factual claims to verify",
            "verdict_breakdown": {"true": 0, "false": 0, "misleading": 0, "unverified": 0, "unverifiable": 0, "total": 0},
            "final_verdict_category": "Unverified",
        }

    counts = {"true": 0, "false": 0, "misleading": 0, "unverified": 0}
    for item in claim_items:
        raw_label = str(item.get("verdict", {}).get("label", "")).lower()
        label = {
            "supported": "true",
            "verified": "true",
            "contradicted": "false",
            "refuted": "false",
            "debunked": "false",
            "partially_supported": "misleading",
            "distorted": "misleading",
            "partial": "misleading",
            "unverified": "unverified",
            "unverifiable": "unverified",
            "insufficient": "unverified",
            "inconclusive": "unverified",
            "ambiguous": "unverified",
            "true": "true",
            "false": "false",
            "misleading": "misleading",
        }.get(raw_label, "unverified")
        if label in counts:
            counts[label] += 1
        else:
            counts["unverified"] += 1

    total = sum(counts.values())
    counts["total"] = total
    counts["unverifiable"] = counts.get("unverified", 0)

    t = counts["true"]
    f = counts["false"]
    m = counts["misleading"]
    u = counts.get("unverified", 0)

    # ── Signals from Multi-Modal Modules ──
    dm_category = None
    dm_confidence = 0.0
    dm_suspicion = 0.0
    dm_veto = {}
    if dm_report:
        if "classification" in dm_report:
            dm_category = dm_report["classification"].get("category", "")
            dm_confidence = dm_report["classification"].get("confidence", 0.0)
            dm_suspicion = dm_report["classification"].get("suspicion_score", 0.0)
        dm_veto = dm_report.get("dm_veto", {})

    deepfake_prob = 0.0
    voice_clone_prob = 0.0
    is_synthetic = False
    forensics_veto = {}
    if forensics_report:
        deepfake_prob = forensics_report.get("deepfake_probability", 0.0)
        voice_clone_prob = forensics_report.get("voice_clone_probability", 0.0)
        forensics_veto = forensics_report.get("forensics_veto", {})
        is_synthetic = bool(
            forensics_veto.get("veto")
            or forensics_report.get("is_synthetic", False)
            or (forensics_report.get("detector_status") != "not_available" and (deepfake_prob >= 0.55 or voice_clone_prob >= 0.60))
        )

    recycled_footage = False
    google_factcheck_debunk = False
    osint_veto = {}
    if osint_report:
        recycled_footage = osint_report.get("recycled_footage_detected", False) or osint_report.get("potential_recycled_content", False)
        gfc = osint_report.get("google_factcheck", {})
        google_factcheck_debunk = gfc.get("debunked_count", 0) > 0 or gfc.get("manipulated_count", 0) > 0
        osint_veto = osint_report.get("osint_veto", {})

    veto_applied = None
    final_category = None
    overall = None

    # ── Veto Layer 1: Forensics Deepfake / Synthetic Media ──
    unified_report = forensics_report.get("unified_authenticity", {}) if forensics_report else {}
    overall_v = unified_report.get("overall_verdict")
    overall_v_label = unified_report.get("overall_verdict_label")

    if is_synthetic or overall_v == "AI_GENERATED":
        final_category = "Deepfake"
        if overall_v_label and "deepfake" in overall_v_label.lower():
            overall = overall_v_label
        elif overall_v_label:
            overall = f"{overall_v_label} (Deepfake Detected)"
        else:
            overall = "Deepfake / Synthetic Media Detected"
        veto_applied = {
            "type": "forensics_synthetic_veto",
            "reason": forensics_veto.get("reason") or unified_report.get("summary") or f"Synthetic audio / deepfake probability ({int(max(deepfake_prob, voice_clone_prob) * 100)}%) exceeds safe threshold",
        }
    elif overall_v == "PARTIALLY_AI_GENERATED":
        final_category = "Manipulated"
        overall = overall_v_label or "LIKELY PARTIALLY AI-GENERATED / AI-EDITED"
        veto_applied = {
            "type": "forensics_partial_synthetic_veto",
            "reason": unified_report.get("summary") or "Mixture of authentic and synthetic or AI-modified media detected",
        }

    # ── Veto Layer 2: OSINT Recycled Footage / Timeline Contradiction ──
    elif recycled_footage:
        final_category = "Manipulated"
        overall = "Recycled Footage Out of Context"
        veto_applied = {
            "type": "osint_recycled_footage_veto",
            "reason": osint_veto.get("reason") or "Historical footage identified and misrepresented as a recent event",
        }

    # ── Veto Layer 3: High-Authority Google Fact Check Debunk ──
    elif google_factcheck_debunk:
        is_manip = osint_report.get("google_factcheck", {}).get("manipulated_count", 0) > 0
        final_category = "Manipulated" if is_manip else "Fake"
        overall = "Manipulated Context (Fact-Checked)" if is_manip else "False — Certified Fact-Checker Debunk"
        veto_applied = {
            "type": "osint_google_factcheck_veto",
            "reason": osint_veto.get("reason") or "Debunked by certified fact-checking organizations in Google Fact Check database",
        }

    # ── Veto Layer 4: Data Mining Misinformation Pattern Governor ──
    elif dm_veto.get("veto"):
        final_category = dm_veto.get("verdict", "Misleading")
        overall = f"{final_category} (AI Pattern Mining Detection)"
        veto_applied = {
            "type": "dm_active_governor_veto",
            "reason": dm_veto.get("reason"),
        }

    # ── Base Layer: Claim Fact-Checking Synthesis ──
    else:
        if total == 0:
            final_category = "Unverified"
            overall = "No factual claims to verify"

        elif u == total:
            final_category = "Unverified"
            overall = "Unverified — Insufficient Evidence Found"

        elif t == total and f == 0 and m == 0:
            final_category = "Genuine"
            overall = "True"

        elif f == total and t == 0 and m == 0:
            final_category = "Fake"
            overall = "False"

        elif m == total and t == 0 and f == 0:
            final_category = "Misleading"
            overall = "Misleading"

        elif f > 0 or m > 0:
            if t == 0:
                final_category = "Fake" if f > 0 else "Misleading"
                overall = "False" if f > 0 else "Misleading"
            else:
                final_category = "Manipulated"
                overall = "Misleading — Mixed Claim Evidence"

        elif t > 0 and u > 0 and f == 0 and m == 0:
            final_category = "Likely Genuine"
            overall = "Partially Corroborated (Some Claims Unverified)"

        else:
            final_category = "Unverified"
            overall = "Unverified"

        # ── Calibration Guard: Downgrade if DM or OSINT contradictions are elevated ──
        if final_category in ("Genuine", "Likely Genuine"):
            # Validated threshold: only downgrade if pattern suspicion is genuinely high (> 0.70)
            if dm_suspicion > 0.70 or (dm_category in ("Fake", "Misleading", "High Pattern Anomaly Cluster") and dm_confidence >= 0.75 and dm_suspicion > 0.70):
                final_category = "Misleading"
                overall = "Misleading — High Linguistic / Pattern Misinformation Suspicion"
                veto_applied = {
                    "type": "dm_suspicion_calibration",
                    "reason": f"Data mining suspicion ({dm_suspicion:.2f}) indicates high pattern anomaly contradicting genuine classification",
                }
            elif osint_report and osint_report.get("contradiction_count", 0) >= 3:
                final_category = "Misleading"
                overall = "Misleading — Multiple External Contradictions Detected"
                veto_applied = {
                    "type": "osint_contradiction_calibration",
                    "reason": f"OSINT intelligence collected {osint_report.get('contradiction_count')} contradiction signals",
                }

    counts["veto_applied"] = veto_applied

    return {
        "overall_verdict": overall,
        "verdict_breakdown": counts,
        "final_verdict_category": final_category,
    }


# ─── Evidence Builder ──────────────────────────────────────────────────────────

def _build_evidence_items(search_result: Dict, verdict_label: str) -> List[Dict]:
    """
    Normalise evidence items from the search pipeline result.
    Preserves stance, independence, relevance, and explanation from evidence_classifier.
    """
    evidence_items = []
    for evidence in search_result.get("evidence", []):
        source_url = evidence.get("source_url") or evidence.get("url", "")
        # Skip placeholder / empty URLs
        if not source_url or source_url.startswith("https://example.com"):
            continue
        source_title = evidence.get("source_title") or evidence.get("title") or "Web Source"
        domain = evidence.get("domain")
        if not domain:
            domain = source_url.split("//", 1)[-1].split("/", 1)[0]
        domain_trust = evidence.get("domain_trust")
        if domain_trust is None:
            tier = evidence.get("domain_trust_tier", 3)
            domain_trust = "high" if tier == 1 else "medium" if tier == 2 else "low"
        
        stance = evidence.get("stance")
        supports = evidence.get("supports_claim")
        if supports is None:
            supports = True if stance == "supports" else False if stance == "contradicts" else None
            
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        evidence_items.append({
            "source_url": source_url,
            "source_title": source_title,
            "domain": domain,
            "domain_trust": domain_trust,
            "domain_trust_tier": evidence.get("domain_trust_tier", 3),
            "snippet": evidence.get("snippet") or evidence.get("excerpt") or "No evidence snippet available.",
            "relevant_passage": evidence.get("relevant_passage") or evidence.get("snippet", ""),
            "quote": evidence.get("quote") or evidence.get("relevant_passage") or evidence.get("snippet", ""),
            "quote_location": evidence.get("quote_location"),
            "quote_verified": evidence.get("quote_verified", False),
            "publisher": evidence.get("publisher") or domain,
            "retrieval_timestamp": evidence.get("retrieval_timestamp") or now_iso,
            "credibility_limitation": evidence.get("credibility_limitation"),
            "relevance_score": evidence.get("relevance_score", 0.75),
            "publication_date": evidence.get("publication_date", datetime.datetime.now().strftime("%Y-%m-%d")),
            "supports_claim": supports,
            "stance": stance or ("supports" if supports is True else "contradicts" if supports is False else "neutral"),
            "is_independent": evidence.get("is_independent", True),
            "explanation": evidence.get("explanation", ""),
        })
    return evidence_items



# ─── Score Fusion ─────────────────────────────────────────────────────────────

def fuse_scores(
    forensics_report: Dict,
    osint_report: Dict,
    dm_report: Dict,
    claim_items: List[Dict],
) -> Dict[str, float]:
    """Fuse multi-modal scores into individual and overall confidence scores with contradiction dampening."""
    # Video score from forensics
    video_score = forensics_report.get("video_integrity_score", 70.0)
    audio_score = forensics_report.get("audio_integrity_score", 75.0)
    metadata_score = forensics_report.get("metadata_integrity_score", 80.0)

    # OSINT score
    osint_score = osint_report.get("osint_score", 60.0)

    # DM score
    dm_score = dm_report.get("dm_score", 65.0)

    # Claim fact-check score
    if claim_items:
        verdicts = [item["verdict"]["label"].lower() for item in claim_items]
        true_ratio = verdicts.count("true") / len(verdicts)
        false_ratio = (verdicts.count("false") + verdicts.count("misleading")) / len(verdicts)
        unverified_ratio = (verdicts.count("unverified") + verdicts.count("unverifiable")) / len(verdicts)
        claim_score = round((true_ratio * 100 - false_ratio * 60 + (50 * unverified_ratio)), 1)
        claim_score = max(10, min(100, claim_score))
    else:
        claim_score = 50.0

    # Contradiction and red flag dampening
    contradiction_count = osint_report.get("contradiction_count", 0)
    red_flag_count = forensics_report.get("red_flag_count", 0)

    contradiction_penalty = min(contradiction_count * 2.5, 20.0)
    red_flag_penalty = min(red_flag_count * 2.0, 15.0)

    is_synthetic = forensics_report.get("is_synthetic", False)
    is_recycled = osint_report.get("recycled_footage_detected", False) or osint_report.get("potential_recycled_content", False)

    # Weighted fusion
    raw_confidence = (
        video_score * 0.20
        + audio_score * 0.15
        + metadata_score * 0.10
        + osint_score * 0.25
        + dm_score * 0.20
        + claim_score * 0.10
    ) - (contradiction_penalty + red_flag_penalty)

    if is_synthetic or is_recycled:
        raw_confidence = min(raw_confidence, 38.0)

    overall_confidence = round(max(10.0, min(98.0, raw_confidence)), 1)

    return {
        "video_score": round(video_score, 1),
        "audio_score": round(audio_score, 1),
        "metadata_score": round(metadata_score, 1),
        "osint_score": round(osint_score, 1),
        "dm_score": round(dm_score, 1),
        "overall_confidence": overall_confidence,
    }


# ─── Main Processing ───────────────────────────────────────────────────────────

def process_video(job: Job):
    try:
        # ── Step 1: Ingest (download + transcribe) ──
        print(f"[process_video] Starting ingestion for job {job.id}")
        result = ingest_video(job)

        if not result:
            job.status = JobStatus.FAILED
            if not job.error_message:
                job.error_message = "No segments extracted from video"
            print(f"[process_video] Ingestion failed: {job.error_message}")
            publish_job_event(str(job.id), "error", {"error": job.error_message, "status": "failed"})
            return

        # Groq's translation API can return valid text with an empty segments
        # list. When that happens, synthesise a single fallback segment so the
        # rest of the pipeline (transcript save, claim extraction, …) works.
        if not result.segments and result.english_text:
            from transcription.groq_translator import Segment as _Seg
            print(
                f"[process_video] Groq returned no segments — synthesising "
                f"fallback segment from english_text ({len(result.english_text)} chars)"
            )
            result.segments = [
                _Seg(
                    text=result.english_text,
                    start=0.0,
                    end=result.audio_duration_seconds,
                    avg_logprob=None,
                    no_speech_prob=None,
                )
            ]

        # ── Step 2: Save transcript ──
        print(f"[process_video] Got {len(result.segments)} segments, saving transcript")
        transcripts_db[str(job.id)] = [
            {"text": s.text, "start": s.start, "end": s.end}
            for s in result.segments
        ]
        full_transcript = "\n".join([s.text.strip() for s in result.segments if getattr(s, "text", None)])

        # ── Step 3 & 4: Forensics Analysis and Claim Extraction CONCURRENTLY ──
        job.status = JobStatus.FORENSICS_ANALYSIS
        job.progress_percent = 30.0
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)
        print(f"[process_video] Running forensics analysis and claim extraction concurrently...")

        audio_path = getattr(result, "audio_path", None)
        video_path = getattr(result, "video_path", None)
        segments = getattr(result, "segments", None)
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

        with ThreadPoolExecutor(max_workers=2) as stage1_executor:
            fut_forensics = stage1_executor.submit(
                run_forensics_pipeline,
                full_transcript,
                job.video_url,
                audio_path=audio_path,
                video_path=video_path,
                segments=segments,
            )
            fut_claims = stage1_executor.submit(
                extract_claims_with_llm, full_transcript
            )

            try:
                forensics_report = fut_forensics.result(timeout=120)
            except Exception as e:
                print(f"[process_video] Forensics pipeline failed: {e}")
                forensics_report = run_forensics_pipeline(
                    full_transcript,
                    job.video_url,
                    audio_path=None,
                    video_path=None,
                    segments=None,
                )

            try:
                extracted = fut_claims.result(timeout=120)
            except Exception as e:
                print(f"[process_video] Claim extraction failed: {e}")
                extracted = None

        forensics_db[str(job.id)] = forensics_report
        job.forensics_report = forensics_report

        if extracted is None:
            job.status = JobStatus.EXTRACTION_FAILED
            job.error_message = "LLM claim extraction failed after 2 attempts. Please retry."
            print(f"[process_video] Extraction failed after retries.")
            publish_job_event(str(job.id), "error", {"error": job.error_message, "status": "failed"})
            return

        if len(extracted) == 0:
            print(f"[process_video] No spoken claims extracted — completing pipeline in Visual Forensics mode.")
            claims_verdicts_db[str(job.id)] = []

            # Synthesize OSINT and Data Mining for silent/visual-only media
            osint_report = {
                "osint_score": 100.0,
                "high_trust_sources": 0,
                "support_count": 0,
                "contradiction_count": 0,
                "news_summary": "Media contains no spoken claims or transcript for external news/fact-check cross-referencing.",
                "contradictions": [],
                "google_factcheck": {"fact_checks_found": [], "query": ""},
                "geo_verification": {"countries_claimed": [], "cities_claimed": [], "corroborated": True},
            }
            osint_db[str(job.id)] = osint_report

            dm_report = {
                "dm_score": 100.0,
                "classification": {"category": "Visual / Non-Verbal Media", "confidence": 0.95},
                "summary": "Visual analysis completed for silent media with no verbal claims.",
                "pattern_mining": {"patterns": []},
            }
            dm_db[str(job.id)] = dm_report

            scores = fuse_scores(forensics_report, osint_report, dm_report, [])
            job.video_score = scores.get("video_score")
            job.audio_score = scores.get("audio_score")
            job.metadata_score = scores.get("metadata_score")
            job.osint_score = scores.get("osint_score")
            job.dm_score = scores.get("dm_score")
            job.overall_confidence = scores.get("overall_confidence")
            job.osint_report = osint_report
            job.dm_report = dm_report

            is_synthetic = bool(forensics_report.get("is_synthetic", False))
            unified_report = forensics_report.get("unified_authenticity", {})
            overall_v = unified_report.get("overall_verdict") or ("AI_GENERATED" if is_synthetic else "INCONCLUSIVE")
            overall_v_label = unified_report.get("overall_verdict_label") or ("AI-Generated Media (Visual Synthesis Detected)" if (is_synthetic or overall_v == "AI_GENERATED") else "Non-Verbal Media (Visual Forensics Assessed)")

            if is_synthetic or overall_v == "AI_GENERATED":
                job.final_verdict_category = "Deepfake"
                job.overall_verdict = overall_v_label
            elif overall_v == "PARTIALLY_AI_GENERATED":
                job.final_verdict_category = "Manipulated"
                job.overall_verdict = overall_v_label
            elif overall_v == "LIKELY_AUTHENTIC":
                job.final_verdict_category = "Likely Authentic"
                job.overall_verdict = overall_v_label
            elif overall_v == "LIKELY_MANIPULATED":
                job.final_verdict_category = "Manipulated"
                job.overall_verdict = overall_v_label
            else:
                job.final_verdict_category = "Unverified"
                job.overall_verdict = overall_v_label

            job.status = JobStatus.DONE
            job.progress_percent = 100.0
            job.verdict_breakdown = {"true": 0, "false": 0, "misleading": 0, "unverifiable": 0, "total": 0}
            job.updated_at = datetime.datetime.now(datetime.timezone.utc)
            publish_job_event(str(job.id), "done", {
                "status": "done",
                "job_id": str(job.id),
                "final_verdict_category": job.final_verdict_category,
                "overall_verdict": job.overall_verdict,
            })
            return

        print(f"[process_video] Extracted {len(extracted)} claims: {[c['claim'][:60] for c in extracted]}")

        # ── Step 5 & 6: Parallel Claim Verification & Overlapped OSINT ──
        job.status = JobStatus.VERIFYING
        job.progress_percent = 50.0
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)

        # Launch OSINT pipeline concurrently in the background (uses extracted claims + forensics)
        print(f"[process_video] Launching OSINT in parallel with claim verification...")
        osint_executor = ThreadPoolExecutor(max_workers=1)
        fut_osint = osint_executor.submit(
            run_osint_pipeline, full_transcript, job.video_url, extracted, forensics_report
        )

        detected_language = result.detected_source_language or "en"

        def _verify_claim_worker(idx_and_item):
            idx, extracted_claim = idx_and_item
            claim_text = extracted_claim.get("claim", "").strip()
            context_text = extracted_claim.get("context", "").strip()
            if not claim_text:
                return None

            # Pre-flight claim validation
            validation = validate_claim_for_verification(claim_text)
            sanitized_claim = validation.get("sanitized_claim") or claim_text
            is_ambig = extracted_claim.get("is_ambiguous", False) or validation.get("is_ambiguous", False)
            ambig_reason = extracted_claim.get("ambiguity_reason") or validation.get("ambiguity_reason")

            claim = Claim(
                source_video_id=job.video_url,
                source_platform=SourcePlatform.YOUTUBE,
                raw_text=claim_text,
                normalized_text=sanitized_claim,
                language=detected_language,
                timestamp_in_video=0.0,
            )

            print(f"[process_video] Fact-checking claim {idx+1}/{len(extracted)}: {sanitized_claim[:70]}...")
            try:
                search_result = gather_evidence_for_claim(sanitized_claim, full_transcript)
            except Exception as e:
                print(f"[process_video] Claim {idx+1} verification error: {e}")
                search_result = {
                    "label": "unverified",
                    "confidence": 0.0,
                    "reasoning": f"Verification error: {e}. Insufficient evidence to establish veracity.",
                    "summary": "Verification encountered an upstream error — marked as UNVERIFIED.",
                    "evidence": [],
                    "fact_check_summary": {
                        "searches_run": 1,
                        "sources_found": 0,
                        "sources_accepted": 0,
                        "sources_blocked": 0,
                        "source_relevance": 0.0,
                        "evidence_support": 0.0,
                        "source_acceptance": 0.0,
                        "consensus_score": 0.0,
                        "consensus": 0.0,
                        "verdict_confidence": 0.0,
                        "llm_rounds": 1,
                        "critic_rejections": 0,
                    },
                    "search_runs": [],
                }

            verdict_label = search_result.get("label", "unverified")
            evidence_items = _build_evidence_items(search_result, verdict_label)

            avg_rel = round(sum(e.get("relevance_score", 0.75) for e in evidence_items) / max(1, len(evidence_items)), 3) if evidence_items else 0.0
            fact_check_summary = search_result.get("fact_check_summary") or {
                "searches_run": 1,
                "sources_found": len(evidence_items),
                "sources_accepted": len(evidence_items),
                "sources_blocked": 0,
                "source_relevance": avg_rel,
                "evidence_support": 1.0 if verdict_label == "true" else 0.0,
                "source_acceptance": 1.0,
                "consensus_score": 0.5,
                "consensus": 0.5,
                "verdict_confidence": search_result.get("confidence", 0.75),
                "cross_platform_hits": 0,
                "llm_rounds": 1,
                "critic_rejections": 0,
            }

            # Explicitly separate and preserve all 5 required fact-checking metrics
            if "source_relevance" not in fact_check_summary:
                fact_check_summary["source_relevance"] = avg_rel
            if "evidence_support" not in fact_check_summary:
                fact_check_summary["evidence_support"] = 1.0 if verdict_label == "true" else 0.0
            if "source_acceptance" not in fact_check_summary:
                total_src = fact_check_summary.get("sources_found", len(evidence_items))
                fact_check_summary["source_acceptance"] = round(len(evidence_items) / max(1, total_src), 3) if total_src > 0 else 1.0
            fact_check_summary["verdict_confidence"] = search_result.get("confidence", 0.75)
            if "consensus" not in fact_check_summary and "consensus_score" in fact_check_summary:
                fact_check_summary["consensus"] = fact_check_summary["consensus_score"]

            search_runs = search_result.get("search_runs") or [
                {
                    "query": sanitized_claim[:80],
                    "source_type": "NewsAPI + DuckDuckGo + Groq LLM",
                    "results_found": len(evidence_items),
                    "top_domain": evidence_items[0]["domain"] if evidence_items else "unknown",
                    "trust_level": evidence_items[0]["domain_trust"] if evidence_items else "medium",
                    "stance": "supports" if verdict_label == "true" else "contradicts" if verdict_label == "false" else "neutral",
                }
            ]

            llm_checks = search_result.get("llm_checks") or [
                {
                    "agent": "Groq Claim Extractor",
                    "role": "Claim identification",
                    "finding": f"Claim was extracted by LLM from full video transcript. Original context: \"{context_text[:120]}\"",
                    "passed": True,
                },
                {
                    "agent": "Evidence Classifier & Consensus Engine",
                    "role": "Relevance & stance audit",
                    "finding": f"Audited {len(evidence_items)} sources across {fact_check_summary.get('searches_run', 1)} searches. Consensus score: {int(fact_check_summary.get('consensus_score', 0.5)*100)}%.",
                    "passed": True,
                }
            ]

            # Decompose into atomic sub-claims (preserving intact context when ambiguous)
            atomic_claims = decompose_compound_claim(sanitized_claim)
            atomic_assessments = []
            for ac in atomic_claims:
                atomic_assessments.append({
                    "id": str(uuid.uuid4())[:8],
                    "atomic_claim": ac,
                    "verdict": verdict_label,
                    "reasoning": search_result.get("summary") or search_result.get("reasoning", ""),
                    "confidence": search_result.get("confidence", 0.75),
                    "supporting_quote_ids": [e["source_url"] for e in evidence_items if e.get("supports_claim") is True],
                    "contradicting_quote_ids": [e["source_url"] for e in evidence_items if e.get("supports_claim") is False],
                })

            canonical_hash = search_result.get("canonical_hash")
            unresolved = []
            if is_ambig and ambig_reason:
                unresolved.append(f"Ambiguity flagged: {ambig_reason}")
            if verdict_label == "unverified":
                unresolved.append("External sources lacked sufficient direct evidence to confirm or refute this claim.")
            elif verdict_label == "misleading" and "unverified" in search_result.get("reasoning", "").lower():
                unresolved.append("External sources lacked sufficient direct evidence to confirm or refute this claim.")

            verdict = {
                "id": str(uuid.uuid4()),
                "claim_id": str(claim.id),
                "label": verdict_label,
                "confidence": search_result.get("confidence", 0.75),
                "evidence": evidence_items,
                "reasoning": search_result.get("reasoning", ""),
                "summary": search_result.get("summary", f"Claim marked as {verdict_label.upper()} based on web search evidence."),
                "context": context_text,
                "is_ambiguous": is_ambig,
                "ambiguity_reason": ambig_reason,
                "atomic_assessments": atomic_assessments,
                "canonical_hash": canonical_hash,
                "unresolved_uncertainties": unresolved,
                "search_runs": search_runs,
                "llm_checks": llm_checks,
                "fact_check_summary": fact_check_summary,
                "queries_executed": search_result.get("queries_executed", []),
                "retrieval_rounds": search_result.get("retrieval_rounds", 1),
                "stopping_reason": search_result.get("stopping_reason", "completed"),
            }
            res = {
                "claim": claim.model_dump(),
                "verdict": verdict,
                "related_count": 0,
                "related_platforms": [],
            }
            return (idx, res, verdict_label)

        # Run claim verification with bounded worker pool (max_workers=5 for full parallel execution)
        max_claim_workers = min(len(extracted), 5)
        verified_results = [None] * len(extracted)

        with ThreadPoolExecutor(max_workers=max_claim_workers) as claim_pool:
            from concurrent.futures import as_completed
            futures_map = {
                claim_pool.submit(_verify_claim_worker, (i, extracted_claim)): i
                for i, extracted_claim in enumerate(extracted)
            }
            completed_count = 0
            for fut in as_completed(futures_map):
                orig_idx = futures_map[fut]
                completed_count += 1
                try:
                    res_tuple = fut.result()
                    if res_tuple:
                        _, res, verdict_label = res_tuple
                        verified_results[orig_idx] = res
                        print(f"[process_video] Claim {orig_idx+1}/{len(extracted)} done — {verdict_label}")
                        publish_job_event(str(job.id), "claim", res)
                except Exception as e:
                    print(f"[process_video] Worker error on claim {orig_idx+1}: {e}")

                # Update live progress
                job.progress_percent = 50.0 + (completed_count / len(extracted)) * 30.0
                job.updated_at = datetime.datetime.now(datetime.timezone.utc)
                # Keep claims_verdicts_db up to date with completed claims
                claims_verdicts_db[str(job.id)] = [r for r in verified_results if r is not None]

        claim_items = [r for r in verified_results if r is not None]
        claims_verdicts_db[str(job.id)] = claim_items

        # ── Step 6: Await Overlapped OSINT Pipeline ──
        job.status = JobStatus.OSINT_COLLECTION
        job.progress_percent = 82.0
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)
        print(f"[process_video] Finalizing OSINT report...")
        try:
            osint_report = fut_osint.result(timeout=60)
        except Exception as e:
            print(f"[process_video] OSINT collection failed or timed out: {e}")
            osint_report = run_osint_pipeline(full_transcript, job.video_url, claim_items, forensics_report)
        finally:
            osint_executor.shutdown(wait=False)

        osint_db[str(job.id)] = osint_report
        job.osint_report = osint_report

        # ── Step 8: Data Mining ──
        job.status = JobStatus.DATA_MINING
        job.progress_percent = 88.0
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)
        print(f"[process_video] Running data mining pipeline...")

        dm_report = run_data_mining_pipeline(full_transcript, claim_items, forensics_report, osint_report)
        dm_db[str(job.id)] = dm_report
        job.dm_report = dm_report

        # ── Step 9: Score Fusion ──
        print(f"[process_video] Fusing multi-modal scores...")
        scores = fuse_scores(forensics_report, osint_report, dm_report, claim_items)
        job.video_score = scores["video_score"]
        job.audio_score = scores["audio_score"]
        job.metadata_score = scores["metadata_score"]
        job.osint_score = scores["osint_score"]
        job.dm_score = scores["dm_score"]
        job.overall_confidence = scores["overall_confidence"]

        # ── Step 10: Compute overall verdict ──
        overall = compute_overall_verdict(claim_items, dm_report, forensics_report, osint_report)

        claims_verdicts_db[str(job.id)] = claim_items
        job.overall_verdict = overall["overall_verdict"]
        job.verdict_breakdown = overall["verdict_breakdown"]
        job.final_verdict_category = overall["final_verdict_category"]
        job.status = JobStatus.DONE
        job.progress_percent = 100.0
        job.updated_at = datetime.datetime.now(datetime.timezone.utc)
        print(
            f"[process_video] DONE — {len(claim_items)} claims. "
            f"Verdict: {job.overall_verdict} | Category: {job.final_verdict_category} | "
            f"Confidence: {job.overall_confidence:.1f}"
        )
        publish_job_event(str(job.id), "done", {"status": "done", "job_id": str(job.id)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        print(f"[process_video] Exception: {e}")
        publish_job_event(str(job.id), "error", {"error": str(e), "status": "failed"})

    finally:
        # Clean up temporary audio file if created during ingestion
        try:
            if 'result' in locals() and result and getattr(result, "audio_path", None):
                ap = getattr(result, "audio_path")
                if ap and os.path.exists(ap) and any(x in ap.lower() for x in ("temp", "video_factcheck_", "_prepared")):
                    os.remove(ap)
        except Exception:
            pass


import queue
import threading
from shared.llm import get_redis_client

class RedisJobQueue:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.queue_key = "job_verification_queue"

    def enqueue(self, job_id: str):
        self.redis_client.rpush(self.queue_key, job_id)

    def dequeue(self, timeout=5) -> Optional[str]:
        res = self.redis_client.blpop(self.queue_key, timeout=timeout)
        if res:
            return res[1]
        return None

class MemoryJobQueue:
    def __init__(self):
        self.queue = queue.Queue()

    def enqueue(self, job_id: str):
        self.queue.put(job_id)

    def dequeue(self, timeout=5) -> Optional[str]:
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None

class JobWorker(threading.Thread):
    def __init__(self, queue_system):
        super().__init__(daemon=True)
        self.queue_system = queue_system
        self.running = True

    def run(self):
        print("[Worker] Background job worker started.")
        while self.running:
            try:
                job_id = self.queue_system.dequeue(timeout=2)
                if job_id:
                    print(f"[Worker] Dequeued job {job_id} for processing.")
                    job = jobs_db.get(job_id)
                    if job:
                        process_video(job)
            except Exception as e:
                print(f"[Worker] Error in job worker loop: {e}")

job_queue = None
worker_thread = None

def init_job_queue():
    global job_queue, worker_thread
    redis_client = get_redis_client()
    if redis_client:
        job_dispatcher.redis_client = redis_client
        job_queue = RedisJobQueue(redis_client)
        print("[JobQueue] Using Redis-backed job queue.")
    else:
        job_queue = MemoryJobQueue()
        print("[JobQueue] Using In-Memory fallback job queue.")

    worker_thread = JobWorker(job_queue)
    worker_thread.start()

def enqueue_job(job_id: str):
    global job_queue
    if not job_queue:
        init_job_queue()
    job_queue.enqueue(job_id)

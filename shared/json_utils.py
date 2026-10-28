"""
json_utils.py — Robust JSON Extraction, Stripping & Truncation Repair
====================================================================
Standard utilities for extracting valid JSON from LLM outputs, removing
markdown code fences, and repairing unclosed quotes, brackets, and braces.
"""

import json
import re
from typing import Any, Optional


def strip_markdown_fences(text: str) -> str:
    """Extract JSON from ```json ... ``` markdown fences or raw text."""
    if not text:
        return ""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()

    if not (text.startswith("{") or text.startswith("[")):
        start_obj = text.find("{")
        start_arr = text.find("[")

        start = -1
        if start_obj != -1 and start_arr != -1:
            start = min(start_obj, start_arr)
        elif start_obj != -1:
            start = start_obj
        elif start_arr != -1:
            start = start_arr

        if start != -1:
            if text[start] == "{":
                end = text.rfind("}") + 1
            else:
                end = text.rfind("]") + 1

            if end > start:
                text = text[start:end]

    return text.strip()


def repair_truncated_json(text: str) -> str:
    """Attempt to close a truncated JSON object or array so it can be parsed using LIFO bracket stack."""
    if not text or not text.strip():
        return text
    t = text.strip()

    # Track unclosed strings and open structural tokens in LIFO order
    in_string = False
    stack = []
    i = 0
    while i < len(t):
        c = t[i]
        if c == "\\" and in_string:
            i += 2
            continue
        if c == '"':
            in_string = not in_string
        elif not in_string:
            if c in ("{", "["):
                stack.append(c)
            elif c == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif c == "]" and stack and stack[-1] == "[":
                stack.pop()
        i += 1

    if in_string:
        t += '"'

    # Remove trailing commas or colons before closing
    t = re.sub(r",\s*$", "", t)
    t = re.sub(r",\s*([\]}])", r"\1", t)

    # Close remaining open brackets in reverse order (LIFO)
    closing_map = {"{": "}", "[": "]"}
    while stack:
        open_tok = stack.pop()
        t += closing_map.get(open_tok, "")

    return t


def parse_llm_json(raw_text: str) -> Optional[Any]:
    """
    Robust multi-strategy parser for LLM JSON responses.
    Attempts direct parse, markdown stripping, comma repairs, and truncation balancing.
    """
    if not raw_text or not raw_text.strip():
        return None

    cleaned = strip_markdown_fences(raw_text)

    # Strategy 1: Direct parse
    try:
        return json.loads(cleaned, strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Comma fix
    try:
        repaired_commas = re.sub(r",\s*([\]}])", r"\1", cleaned)
        return json.loads(repaired_commas, strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 3: Truncation balance
    repaired_struct = repair_truncated_json(cleaned)
    try:
        return json.loads(repaired_struct, strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 4: Trailing comma fix on repaired struct
    try:
        repaired_both = re.sub(r",\s*([\]}])", r"\1", repaired_struct)
        return json.loads(repaired_both, strict=False)
    except (json.JSONDecodeError, ValueError):
        pass

    return None

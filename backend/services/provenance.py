"""
provenance.py — Media Provenance & C2PA Content Credentials Inspector
======================================================================
Calculates SHA-256 hash of original media and inspects C2PA Content Credentials.
Handles 4 distinct states:
  - verified: Valid cryptographic signature and trusted manifest
  - invalid: Tampered or invalid cryptographic manifest
  - missing: No Content Credentials present (not proof of tampering)
  - unsupported: Container format or environment does not support C2PA inspection
"""

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Try importing c2pa-python SDK
try:
    import c2pa
    HAS_C2PA = True
except ImportError:
    HAS_C2PA = False
    logger.info("c2pa-python is not installed. C2PA inspection will report 'unsupported'.")


def compute_file_sha256(file_path: str, chunk_size: int = 65536) -> Optional[str]:
    """Compute cryptographic SHA-256 digest of original media file."""
    if not file_path or not os.path.isfile(file_path):
        return None
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.warning(f"Error computing SHA-256 for {file_path}: {e}")
        return None


def inspect_c2pa_manifest(file_path: str) -> Dict[str, Any]:
    """
    Inspect C2PA Content Credentials of a media file.
    Returns structured provenance dictionary with distinct states:
    verified | invalid | missing | unsupported.
    """
    if not file_path or not os.path.isfile(file_path):
        return {
            "status": "unsupported",
            "reason": "File not provided or not accessible on filesystem",
            "is_valid": False,
            "manifest_found": False,
            "generator": None,
            "issuer": None,
            "claim_history": [],
            "actions": [],
            "signature_details": None,
            "disclaimer": (
                "Absence of C2PA credentials is standard for organic web media "
                "and does NOT imply synthetic manipulation."
            ),
        }

    if not HAS_C2PA:
        return {
            "status": "unsupported",
            "reason": "c2pa-python runtime library not installed in this environment",
            "is_valid": False,
            "manifest_found": False,
            "generator": None,
            "issuer": None,
            "claim_history": [],
            "actions": [],
            "signature_details": None,
            "disclaimer": (
                "C2PA validator unavailable. Absence of Content Credentials does NOT imply manipulation."
            ),
        }

    try:
        # Use c2pa Reader API
        with open(file_path, "rb") as f:
            reader = c2pa.Reader.try_create(stream=f)
            if reader is None:
                return {
                    "status": "missing",
                    "reason": "No C2PA manifest found embedded in media container",
                    "is_valid": False,
                    "manifest_found": False,
                    "generator": None,
                    "issuer": None,
                    "claim_history": [],
                    "actions": [],
                    "signature_details": None,
                    "disclaimer": (
                        "No Content Credentials found. Most online media lacks C2PA metadata; "
                        "absence of credentials is never proof of AI generation or editing."
                    ),
                }

            manifest_json_str = reader.json()

        data = json.loads(manifest_json_str)
        active_manifest = data.get("active_manifest") or {}
        manifests = data.get("manifests", {})
        target = manifests.get(active_manifest, {}) if active_manifest else {}

        # Signature validation details
        validation_status = data.get("validation_status", [])
        is_valid = True
        invalid_reasons = []
        for status_item in validation_status:
            code = status_item.get("code", "")
            if "invalid" in code.lower() or "failed" in code.lower() or "error" in code.lower():
                is_valid = False
                invalid_reasons.append(status_item.get("explanation") or code)

        claim_generator = target.get("claim_generator")
        issuer = target.get("signature_info", {}).get("issuer")
        actions = []
        for assertion in target.get("assertions", []):
            if assertion.get("label") == "c2pa.actions":
                actions.extend(assertion.get("data", {}).get("actions", []))

        status = "verified" if is_valid else "invalid"

        return {
            "status": status,
            "reason": "; ".join(invalid_reasons) if not is_valid else "Cryptographic signature and manifest verified",
            "is_valid": is_valid,
            "manifest_found": True,
            "generator": claim_generator,
            "issuer": issuer,
            "claim_history": list(manifests.keys()),
            "actions": actions,
            "signature_details": target.get("signature_info"),
            "disclaimer": (
                "C2PA Content Credentials provide cryptographic provenance from the issuer. "
                "Verified credentials authenticate the recording tool or workflow."
            ),
        }

    except Exception as e:
        err_msg = str(e)
        if (
            "manifest not found" in err_msg.lower()
            or "nomatchingmanifest" in err_msg.lower()
            or "manifestnotfound" in err_msg.lower()
            or "resource not found" in err_msg.lower()
        ):
            return {
                "status": "missing",
                "reason": "No C2PA manifest found in container",
                "is_valid": False,
                "manifest_found": False,
                "generator": None,
                "issuer": None,
                "claim_history": [],
                "actions": [],
                "signature_details": None,
                "disclaimer": (
                    "No C2PA Content Credentials found. Absence of credentials does NOT prove manipulation."
                ),
            }
        logger.warning(f"Error inspecting C2PA for {file_path}: {e}")
        return {
            "status": "invalid" if "corrupt" in err_msg.lower() or "signature" in err_msg.lower() else "unsupported",
            "reason": f"C2PA inspection encountered error: {err_msg}",
            "is_valid": False,
            "manifest_found": False,
            "generator": None,
            "issuer": None,
            "claim_history": [],
            "actions": [],
            "signature_details": None,
            "disclaimer": (
                "Inspection error encountered during C2PA parsing. Credentials could not be confirmed."
            ),
        }


def analyze_media_provenance(file_path: Optional[str]) -> Dict[str, Any]:
    """
    Combined provenance analysis:
    - Original file SHA-256 hash
    - C2PA Content Credentials
    - File size and basic container checks
    """
    if not file_path or not os.path.isfile(file_path):
        return {
            "status": "not_assessed",
            "sha256": None,
            "c2pa": {
                "status": "unsupported",
                "reason": "No local file available for provenance inspection",
                "is_valid": False,
                "manifest_found": False,
                "generator": None,
                "issuer": None,
                "actions": [],
                "disclaimer": "Absence of credentials does not imply manipulation.",
            },
            "file_size_bytes": None,
        }

    sha256_hash = compute_file_sha256(file_path)
    c2pa_res = inspect_c2pa_manifest(file_path)
    file_size = os.path.getsize(file_path)

    return {
        "status": "assessed",
        "sha256": sha256_hash,
        "c2pa": c2pa_res,
        "file_size_bytes": file_size,
    }

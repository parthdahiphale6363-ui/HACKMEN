"""
security_validation.py — Ingestion & SSRF Protection
=====================================================
Validates externally supplied URLs and media files before processing.
Protects against SSRF, internal network scanning, cloud metadata access,
and malicious/corrupted payloads.
"""

import ipaddress
import logging
import os
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Cloud metadata addresses to strictly reject
BLOCKED_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure instance metadata
    "metadata.google.internal",
    "100.100.100.200",  # Alibaba Cloud metadata
}

# Supported media magic bytes signatures
MEDIA_SIGNATURES = [
    (b"\x00\x00\x00", b"ftyp"),          # MP4 / M4A / MOV
    (b"RIFF", b"WAVE"),                  # WAV
    (b"RIFF", b"AVI "),                  # AVI
    (b"\x1a\x45\xdf\xa3", None),         # WebM / MKV
    (b"ID3", None),                      # MP3 with ID3 tag
    (b"\xff\xfb", None),                 # MP3 sync frame
    (b"\xff\xf3", None),                 # MP3 sync frame
    (b"\xff\xf2", None),                 # MP3 sync frame
    (b"OggS", None),                     # OGG
    (b"fLaC", None),                     # FLAC
]

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB max


class SecurityValidationError(Exception):
    """Raised when media URL or file fails security checks."""
    pass


def is_private_or_restricted_ip(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, link-local, or multicast."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
            or ip.is_reserved
        )
    except ValueError:
        return True


def validate_media_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a given media URL is safe to retrieve:
    1. Must use http or https scheme.
    2. Hostname must resolve to a public, non-reserved IP.
    3. Hostname cannot be cloud metadata.
    """
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL"

    try:
        parsed = urlparse(url.strip())
    except Exception as e:
        return False, f"Malformed URL syntax: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported scheme '{parsed.scheme}': only HTTP/HTTPS are allowed"

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in URL"

    if hostname.lower() in BLOCKED_IPS:
        return False, f"Access to cloud metadata host '{hostname}' is blocked"

    # Resolve hostname to IPv4/IPv6 addresses
    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or 80, proto=socket.IPPROTO_TCP)
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if ip_str in BLOCKED_IPS:
                return False, f"Target IP '{ip_str}' is a blocked metadata address"
            if is_private_or_restricted_ip(ip_str):
                return False, f"Target IP '{ip_str}' resolves to a private or restricted network address"
    except socket.gaierror as e:
        # DNS resolution error
        return False, f"Could not resolve host '{hostname}': {e}"
    except Exception as e:
        return False, f"DNS resolution validation failed: {e}"

    return True, None


def validate_media_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a local media file:
    1. File must exist and be accessible.
    2. File size must be within safe limits.
    3. File must match known media container magic bytes.
    """
    if not file_path or not os.path.isfile(file_path):
        return False, "File does not exist or is not a regular file"

    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty (0 bytes)"
        if file_size > MAX_FILE_SIZE_BYTES:
            return False, f"File exceeds maximum allowed size ({file_size} > {MAX_FILE_SIZE_BYTES} bytes)"

        with open(file_path, "rb") as f:
            header = f.read(64)

        if len(header) < 4:
            return False, "File is too small to contain valid media headers"

        matched = False
        for prefix, secondary in MEDIA_SIGNATURES:
            if header.startswith(prefix):
                if secondary is None:
                    matched = True
                    break
                elif secondary in header[:16]:
                    matched = True
                    break
            # Also check if secondary (e.g. 'ftyp') appears within the first 16 bytes (standard MP4 offset)
            elif secondary and secondary in header[:16]:
                matched = True
                break

        if not matched:
            logger.warning(f"File {file_path} header does not match known audio/video signatures.")
            # Note: We return False with warning for unknown binary, but allow if ffmpeg can handle it in pipeline
            return False, "Header does not match recognized audio or video container signatures"

        return True, None
    except Exception as e:
        return False, f"File validation error: {e}"

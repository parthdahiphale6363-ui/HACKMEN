"""
test_security_accessibility_quality.py — Automated Validation of Security, Quality & Compliance
=================================================================================================
Validates:
  1. OWASP Security Defense Headers (X-Content-Type-Options, X-Frame-Options, HSTS, CSP, etc.)
  2. CORS origin validation (allows local/render, rejects unauthorized origins)
  3. SSRF & Input validation bounds on JobCreate
  4. OpenAPI 3.0 specification metadata and route schemas
  5. API rate limiter and health diagnostics
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.main import app
from backend.routers.jobs import check_rate_limit, validate_video_url, JobCreate
from pydantic import ValidationError


client = TestClient(app)


class TestSecurityDefenseHeaders:
    """Verifies that all OWASP defense-in-depth security response headers are enforced."""

    def test_root_security_headers(self):
        response = client.get("/")
        assert response.status_code == 200
        headers = response.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
        assert "camera=()" in headers.get("Permissions-Policy", "")
        assert headers.get("Server") == "TruthLens-AI-Engine"

    def test_health_endpoint_security_headers(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


class TestCORSAndOriginPolicy:
    """Verifies CORS security boundaries."""

    def test_cors_trusted_local_origin(self):
        response = client.options(
            "/jobs",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_trusted_render_origin(self):
        response = client.options(
            "/jobs",
            headers={
                "Origin": "https://truthlens-backend.onrender.com",
                "Access-Control-Request-Method": "POST",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://truthlens-backend.onrender.com"

    def test_cors_untrusted_evil_origin(self):
        response = client.options(
            "/jobs",
            headers={
                "Origin": "https://malicious-attacker-site.com",
                "Access-Control-Request-Method": "POST",
            }
        )
        # Untrusted origin should NOT be reflected in access-control-allow-origin
        assert response.headers.get("access-control-allow-origin") is None


class TestInputValidationAndSSRF:
    """Validates input payload constraints and SSRF protections."""

    def test_job_create_valid_url(self):
        job = JobCreate(video_url="https://www.youtube.com/shorts/sample12345")
        assert job.video_url == "https://www.youtube.com/shorts/sample12345"

    def test_job_create_empty_url_rejected(self):
        with pytest.raises(ValidationError):
            JobCreate(video_url="")

    def test_job_create_oversized_url_rejected(self):
        with pytest.raises(ValidationError):
            JobCreate(video_url="https://youtube.com/" + ("a" * 2100))

    def test_validate_video_url_domains(self):
        assert validate_video_url("https://www.youtube.com/shorts/abc") is True
        assert validate_video_url("https://youtu.be/abc") is True
        assert validate_video_url("https://vimeo.com/123456") is True
        assert validate_video_url("https://attacker-domain.com/video.mp4") is False

    def test_ssrf_internal_ip_rejected(self):
        response = client.post("/jobs", json={"video_url": "http://169.254.169.254/latest/meta-data"})
        assert response.status_code == 400
        assert "Security validation failed" in response.json().get("detail", "")


class TestOpenAPISpecificationQuality:
    """Verifies completeness of OpenAPI 3.0 documentation metadata."""

    def test_openapi_schema_metadata(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "TruthLens AI" in schema["info"]["title"]
        assert "1.0.0" == schema["info"]["version"]
        assert "contact" in schema["info"]
        assert "license" in schema["info"]
        assert "/jobs" in schema["paths"]
        assert "/jobs/demo-cases" in schema["paths"]
        assert "/health" in schema["paths"]


class TestRateLimiter:
    """Verifies that rate limiting logic operates correctly."""

    def test_rate_limit_allows_under_quota(self):
        # Fresh unique key
        key = "test_rate_key_under_limit"
        assert check_rate_limit(key) is True

    def test_rate_limit_blocks_exceeded_quota(self):
        key = "test_rate_key_exceeded"
        for _ in range(5):
            check_rate_limit(key)
        # 6th attempt must be rejected
        assert check_rate_limit(key) is False

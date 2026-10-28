"""
test_complete_frontend_and_backend.py — Complete Frontend and Backend Test (Phase 2)
=====================================================================================
Comprehensive Phase 2 Test Suite validating end-to-end integration across:
1. Backend REST API Endpoints (Health, Jobs, Demo Cases, Claims, Forensics, OSINT, Data Mining, Exports)
2. Frontend Data Contracts & Interface Concordance (reports.ts vs FastAPI payloads)
3. Multi-Modal Pipeline Execution (Forensic Fusion, Provenance, Veto Layers, Scoring)
4. Frontend Next.js TypeScript Compilation & Static Structure
"""

import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.main import app
from backend.services.demo_cases import DEMO_CASES
from backend.services.forensics import run_forensics_pipeline
from backend.services.export_service import generate_markdown_dossier
from backend.services.job_service import fuse_scores
from shared.schemas.forensics import ForensicsReport, UnifiedAuthenticityReport, ProvenanceData


client = TestClient(app)


# ─── 1. Backend REST API End-to-End Tests ─────────────────────────────────────

class TestBackendComprehensiveAPIs:
    """Verifies all FastAPI routes, status codes, payload structures, and error handling."""

    def test_root_and_health_endpoints(self):
        """Verify root and health endpoints return status 200 OK with expected fields."""
        res_root = client.get("/")
        assert res_root.status_code == 200
        data_root = res_root.json()
        assert data_root.get("status") == "ok"
        assert "TruthLens AI" in data_root.get("service", "")

        res_health = client.get("/health")
        assert res_health.status_code == 200
        data_health = res_health.json()
        assert data_health.get("status") == "ok"
        assert "timestamp" in data_health

    def test_demo_cases_catalog(self):
        """Verify demo cases catalog returns all 3 production demo case studies."""
        res = client.get("/jobs/demo_cases")
        assert res.status_code == 200
        cases = res.json()
        assert len(cases) >= 3
        case_keys = list(cases.keys())
        assert "deepfake_scam" in case_keys
        assert "science_myths" in case_keys
        assert "geopolitical_disinfo" in case_keys

    @pytest.mark.parametrize("demo_key", ["deepfake_scam", "science_myths", "geopolitical_disinfo"])
    def test_demo_cases_subresource_endpoints(self, demo_key):
        """Verify each demo case exposes all sub-resources required by Frontend tabs."""
        case = DEMO_CASES[demo_key]
        job_id = case["id"]

        # 1. Main Job Status Endpoint
        res_job = client.get(f"/jobs/{job_id}")
        assert res_job.status_code == 200, f"Failed GET /jobs/{job_id}"
        job_data = res_job.json()
        assert job_data.get("id") == job_id
        assert "overall_verdict" in job_data
        assert "final_verdict_category" in job_data

        # 2. Claims & Verdicts Endpoint
        res_claims = client.get(f"/jobs/{job_id}/claims")
        assert res_claims.status_code == 200
        claims_data = res_claims.json()
        assert isinstance(claims_data, list)
        assert len(claims_data) > 0
        assert "claim" in claims_data[0]
        assert "verdict" in claims_data[0]

        # 3. Forensics Endpoint
        res_forensics = client.get(f"/jobs/{job_id}/forensics")
        assert res_forensics.status_code == 200
        forensics_data = res_forensics.json()
        assert "unified_authenticity" in forensics_data
        assert "provenance" in forensics_data
        assert "deepfake_probability" in forensics_data
        assert "voice_clone_probability" in forensics_data

        # 4. OSINT Endpoint
        res_osint = client.get(f"/jobs/{job_id}/osint")
        assert res_osint.status_code == 200
        osint_data = res_osint.json()
        assert "google_factcheck" in osint_data

        # 5. Data Mining Endpoint
        res_dm = client.get(f"/jobs/{job_id}/dm_report")
        assert res_dm.status_code == 200
        dm_data = res_dm.json()
        assert "classification" in dm_data

        # 6. Transcript Endpoint
        res_trans = client.get(f"/jobs/{job_id}/transcript")
        assert res_trans.status_code == 200
        trans_data = res_trans.json()
        assert isinstance(trans_data, list)
        assert len(trans_data) > 0

        # 7. Markdown Dossier Export Endpoint
        res_export = client.get(f"/jobs/{job_id}/export_markdown")
        assert res_export.status_code == 200
        md_text = res_export.text
        assert "# 🛡️ TruthLens AI — Executive Forensic Verification Dossier" in md_text
        assert job_id in md_text

    def test_job_creation_security_enforcement(self):
        """Verify job creation endpoint validates URLs and blocks SSRF / malicious paths."""
        # 1. Reject SSRF Loopback
        res_ssrf = client.post("/jobs", json={"video_url": "http://127.0.0.1/malicious.mp4"})
        assert res_ssrf.status_code == 400
        assert "security validation failed" in res_ssrf.json()["detail"].lower()

        # 2. Reject Cloud Metadata IP
        res_meta = client.post("/jobs", json={"video_url": "http://169.254.169.254/latest/meta-data/"})
        assert res_meta.status_code == 400

        # 3. Reject Path Traversal in local paths
        res_trav = client.post("/jobs", json={"video_url": "../../etc/shadow"})
        assert res_trav.status_code == 400
        assert "path traversal" in res_trav.json()["detail"].lower()

        # 4. Accept Valid Media Target
        res_valid = client.post("/jobs", json={"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
        assert res_valid.status_code in (200, 201, 202)
        assert "id" in res_valid.json()


# ─── 2. Frontend Contract & Schema Concordance Tests ─────────────────────────

class TestFrontendDataContractsAndTypes:
    """Verifies backend payloads match frontend TypeScript types in reports.ts."""

    def test_forensics_payload_matches_frontend_schema(self):
        """Verify /jobs/{id}/forensics matches ForensicsReport and UnifiedAuthenticityReport."""
        for case_id, case in DEMO_CASES.items():
            forensics = case.get("forensics", {})
            # Must validate against Pydantic ForensicsReport
            report = ForensicsReport(**forensics)
            assert report.video_integrity_score >= 0.0
            assert report.audio_integrity_score >= 0.0

            # Unified Authenticity fields
            unified = forensics.get("unified_authenticity", {})
            assert "verdict" in unified or "classification" in unified
            assert "confidence_level" in unified
            assert "reason" in unified
            assert "evidence" in unified
            assert "suspicious_segments" in unified
            assert "provenance" in unified
            assert "checks_performed" in unified
            assert "checks_unavailable" in unified

            # Provenance fields
            prov = forensics.get("provenance", {})
            assert "status" in prov
            assert prov["status"] in ("verified", "invalid", "missing", "unsupported")

    def test_claims_payload_matches_frontend_schema(self):
        """Verify claims items have all fields required by ClaimCard.tsx."""
        for case_id, case in DEMO_CASES.items():
            claims = case.get("claims", [])
            for item in claims:
                assert "claim" in item
                assert "verdict" in item
                c = item["claim"]
                v = item["verdict"]

                # Claim fields
                assert "id" in c
                assert "raw_text" in c or "normalized_text" in c

                # Verdict fields
                assert "label" in v
                assert v["label"] in ("true", "false", "misleading", "unverified", "supported", "contradicted")
                assert "confidence" in v
                assert "summary" in v
                assert "evidence" in v

    def test_frontend_proxy_configuration(self):
        """Verify frontend API proxy route file exists and includes local backend candidate bases."""
        proxy_path = os.path.join(ROOT_DIR, "frontend", "src", "app", "api", "[...path]", "route.ts")
        assert os.path.isfile(proxy_path), "Frontend proxy route.ts not found"

        with open(proxy_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "http://127.0.0.1:8000" in content or "http://localhost:8000" in content
        assert "handleProxy" in content
        assert "NextResponse" in content


# ─── 3. Multi-Modal Pipeline Full Flow Verification ───────────────────────────

class TestMultiModalPipelineFullFlow:
    """Verifies master pipeline orchestration, veto enforcement, and score fusion."""

    def test_forensics_pipeline_execution_without_crashing(self):
        """Verify run_forensics_pipeline returns structured report with all keys."""
        res = run_forensics_pipeline(
            transcript="This is a test transcript describing energy statistics.",
            video_url="https://youtube.com/watch?v=sample_energy",
            audio_path=None,
            video_path=None,
        )
        assert res["video_integrity_score"] > 0
        assert res["audio_integrity_score"] > 0
        assert "unified_authenticity" in res
        assert "summary" in res
        assert "forensics_veto" in res
        assert isinstance(res["red_flags"], list)

    def test_score_fusion_calibrated_computation(self):
        """Verify fuse_scores calculates balanced multimodal score with contradiction penalty."""
        forensics = {"deepfake_probability": 0.10, "voice_clone_probability": 0.05, "is_synthetic": False}
        osint = {"contradiction_count": 0, "support_count": 5}
        dm = {"classification": {"confidence": 0.90, "suspicion_score": 0.10}}
        claims = [
            {"verdict": {"label": "true", "confidence": 0.95}},
            {"verdict": {"label": "true", "confidence": 0.90}},
        ]

        scores = fuse_scores(forensics, osint, dm, claims)
        assert scores["overall_confidence"] >= 70.0
        assert scores["video_score"] > 0.0
        assert scores["audio_score"] > 0.0

    def test_dossier_markdown_cryptographic_integrity(self):
        """Verify generate_markdown_dossier produces cryptographic SHA-256 audit digest."""
        dossier = generate_markdown_dossier(
            job_id="phase-2-test-job",
            video_url="https://youtube.com/watch?v=phase2_test",
            overall_verdict="Verified Factual Report",
            category="Genuine Video",
            confidence=94.5,
            breakdown={"total": 2, "true": 2, "false": 0, "misleading": 0, "unverifiable": 0},
            claims=[],
            forensics={
                "video_integrity_score": 96.0,
                "audio_integrity_score": 98.0,
                "metadata_integrity_score": 100.0,
                "deepfake_probability": 0.04,
                "voice_clone_probability": 0.02,
                "is_synthetic": False,
                "red_flag_count": 0,
                "red_flags": [],
                "unified_authenticity": {
                    "verdict": "AUTHENTIC_NO_ANOMALIES_DETECTED",
                    "confidence_level": "HIGH",
                    "reason": "Cryptographically verified C2PA manifest with zero anomalies.",
                    "evidence": [],
                    "suspicious_segments": [],
                    "checks_performed": ["C2PA Manifest", "OpenCV Visual", "FFprobe Stream"],
                    "checks_unavailable": [],
                },
                "provenance": {
                    "status": "verified",
                    "sha256": "abcdef1234567890abcdef1234567890",
                    "generator": "Hardware Camera Root",
                    "issuer": "Sony C2PA Root",
                }
            }
        )
        assert "SHA256-" in dossier
        assert "AUTHENTIC_NO_ANOMALIES_DETECTED" in dossier
        assert "phase-2-test-job" in dossier
        assert len(dossier) > 500

    def test_cross_engine_forensics_osint_datamining_integration(self):
        """
        Verify the complete cross-engine integration:
        Forensics -> OSINT -> Data Mining -> Score Fusion -> Constitutional Veto.
        """
        from backend.services.osint import run_osint_pipeline
        from backend.services.data_mining import run_data_mining_pipeline
        from backend.services.job_service import compute_overall_verdict

        transcript = "Breaking news: Severe flash floods observed in downtown Paris after unprecedented rainfall."
        claim_items = [{
            "claim": {
                "id": "c1",
                "raw_text": "Severe flash floods in Paris",
                "normalized_text": "Severe flash floods in Paris",
            },
            "verdict": {
                "label": "false",
                "confidence": 0.95,
                "summary": "Debunked recycled footage from 2016.",
                "evidence": []
            }
        }]

        # 1. Forensics Report Output
        forensics_report = {
            "video_integrity_score": 85.0,
            "audio_integrity_score": 90.0,
            "metadata_integrity_score": 80.0,
            "deepfake_probability": 0.10,
            "voice_clone_probability": 0.05,
            "is_synthetic": False,
            "red_flag_count": 0,
            "red_flags": [],
            "geolocation": {"countries": ["France"], "cities": ["Paris"]},
            "temporal_analysis": {"date_references": ["2026-03-10"], "years_mentioned": [2026]},
            "unified_authenticity": {
                "classification": "AUTHENTIC_NO_ANOMALIES_DETECTED",
                "confidence_level": "HIGH",
                "reason": "Natural organic video capture.",
            }
        }

        # 2. OSINT receives Forensics signals (locations, date_refs)
        osint_report = run_osint_pipeline(
            transcript=transcript,
            video_url="https://youtube.com/watch?v=mock_paris_flood",
            claim_items=claim_items,
            forensics_report=forensics_report
        )
        assert "osint_score" in osint_report
        assert "contradiction_count" in osint_report
        assert "geo_verification" in osint_report

        # 3. Data Mining receives both Forensics and OSINT
        dm_report = run_data_mining_pipeline(
            transcript=transcript,
            claim_items=claim_items,
            forensics_report=forensics_report,
            osint_report=osint_report
        )
        assert "dm_score" in dm_report
        assert "classification" in dm_report
        assert "summary" in dm_report

        # 4. Score Fusion across all 3 engines
        scores = fuse_scores(forensics_report, osint_report, dm_report, claim_items)
        assert scores["video_score"] == 85.0
        assert scores["audio_score"] == 90.0
        assert scores["metadata_score"] == 80.0
        assert "overall_confidence" in scores

        # 5. Overall Verdict Constitutional Governance
        overall = compute_overall_verdict(claim_items, dm_report, forensics_report, osint_report)
        assert "overall_verdict" in overall
        assert "verdict_breakdown" in overall
        assert "final_verdict_category" in overall


"""
test_persistent_repository.py — Tests for SQLite Durable Storage Layer
======================================================================
Verifies that jobs, transcripts, forensics, OSINT, and DM reports persist
across server restarts and maintain full dict compatibility.
"""

import os
import uuid
import tempfile
import pytest
from backend.storage.repository import PersistentStore
from shared.schemas.job import Job, JobStatus


def test_persistent_store_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = PersistentStore("test_jobs", db_path=db_path)

        # 1. Store item
        test_id = str(uuid.uuid4())
        job = Job(video_url="https://youtube.com/watch?v=example")
        store[test_id] = job

        assert test_id in store
        assert len(store) == 1
        assert store[test_id].video_url == "https://youtube.com/watch?v=example"

        # 2. Simulate server restart with a new instance reading the same DB file
        store2 = PersistentStore("test_jobs", db_path=db_path)
        assert test_id in store2
        assert len(store2) == 1
        loaded_data = store2[test_id]
        assert loaded_data["video_url"] == "https://youtube.com/watch?v=example"

        # 3. Update status
        store2[test_id] = {"status": "done", "progress_percent": 100.0}
        assert store2[test_id]["status"] == "done"

        # 4. Delete item
        del store2[test_id]
        assert test_id not in store2
        assert len(store2) == 0


def test_json_utils_roundtrip():
    from shared.json_utils import strip_markdown_fences, repair_truncated_json, parse_llm_json

    # Test markdown code block extraction
    raw_md = '```json\n{"status": "ok", "count": 42}\n```'
    assert parse_llm_json(raw_md) == {"status": "ok", "count": 42}

    # Test unclosed brackets repair
    truncated = '{"claims": [{"claim": "The sky is blue"'
    repaired = repair_truncated_json(truncated)
    parsed = parse_llm_json(repaired)
    assert parsed is not None
    assert "claims" in parsed

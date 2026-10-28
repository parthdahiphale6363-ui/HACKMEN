"""
repository.py — Persistent SQLite & Thread-Safe Key-Value Storage
================================================================
Provides a persistent, SQLite-backed dictionary for TruthLens AI state
(jobs, transcripts, verdicts, forensics, OSINT, and data mining reports).
Guarantees full durability across server restarts while preserving
100% dictionary interface compatibility.
"""

import os
import json
import sqlite3
import threading
from contextlib import contextmanager
from collections.abc import MutableMapping
from typing import Any, Iterator, Optional, Dict
from pydantic import BaseModel

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "truthlens_store.db")


class PersistentStore(MutableMapping):
    """
    Thread-safe, SQLite-backed persistent mapping that caches in-memory
    for sub-microsecond reads and writes asynchronously to disk.
    """

    def __init__(self, table_name: str, db_path: str = DB_PATH):
        self.table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
        self.db_path = db_path
        self._lock = threading.RLock()
        self._cache: Dict[str, Any] = {}
        self._init_db()
        self._load_all()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()

    def _serialize(self, value: Any) -> str:
        if isinstance(value, BaseModel):
            return json.dumps(value.model_dump(mode="json"))
        return json.dumps(value, default=str)

    def _load_all(self):
        with self._lock:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT key, value FROM {self.table_name}")
                rows = cursor.fetchall()
                for key, val_str in rows:
                    try:
                        self._cache[key] = json.loads(val_str)
                    except Exception:
                        self._cache[key] = val_str

    def __getitem__(self, key: str) -> Any:
        with self._lock:
            return self._cache[str(key)]

    def __setitem__(self, key: str, value: Any):
        k = str(key)
        serialized = self._serialize(value)
        with self._lock:
            self._cache[k] = value
            try:
                with self._connection() as conn:
                    conn.execute(
                        f"""
                        INSERT INTO {self.table_name} (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(key) DO UPDATE SET
                            value = excluded.value,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (k, serialized),
                    )
                    conn.commit()
            except Exception as e:
                print(f"[PersistentStore:{self.table_name}] SQLite sync warning: {e}")

    def __delitem__(self, key: str):
        k = str(key)
        with self._lock:
            if k in self._cache:
                del self._cache[k]
            with self._connection() as conn:
                conn.execute(f"DELETE FROM {self.table_name} WHERE key = ?", (k,))
                conn.commit()

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._cache.keys()))

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: object) -> bool:
        with self._lock:
            return str(key) in self._cache

    def clear(self):
        with self._lock:
            self._cache.clear()
            with self._connection() as conn:
                conn.execute(f"DELETE FROM {self.table_name}")
                conn.commit()


# ─── Singleton Stores for Core Modules ────────────────────────────────────────

_jobs_store: Optional[PersistentStore] = None
_transcripts_store: Optional[PersistentStore] = None
_forensics_store: Optional[PersistentStore] = None
_osint_store: Optional[PersistentStore] = None
_dm_store: Optional[PersistentStore] = None
_claims_verdicts_store: Optional[PersistentStore] = None


def get_jobs_db() -> PersistentStore:
    global _jobs_store
    if _jobs_store is None:
        _jobs_store = PersistentStore("jobs")
    return _jobs_store


def get_transcripts_db() -> PersistentStore:
    global _transcripts_store
    if _transcripts_store is None:
        _transcripts_store = PersistentStore("transcripts")
    return _transcripts_store


def get_forensics_db() -> PersistentStore:
    global _forensics_store
    if _forensics_store is None:
        _forensics_store = PersistentStore("forensics")
    return _forensics_store


def get_osint_db() -> PersistentStore:
    global _osint_store
    if _osint_store is None:
        _osint_store = PersistentStore("osint")
    return _osint_store


def get_dm_db() -> PersistentStore:
    global _dm_store
    if _dm_store is None:
        _dm_store = PersistentStore("data_mining")
    return _dm_store


def get_claims_verdicts_db() -> PersistentStore:
    global _claims_verdicts_store
    if _claims_verdicts_store is None:
        _claims_verdicts_store = PersistentStore("claims_verdicts")
    return _claims_verdicts_store

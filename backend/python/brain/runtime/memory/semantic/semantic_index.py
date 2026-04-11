from __future__ import annotations

import json
import os
import sqlite3
import threading
import tempfile
import weakref
from hashlib import sha1
from pathlib import Path

from .models import SemanticFact


class SemanticIndex:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.db_dir = root / ".logs" / "fusion-runtime" / "memory" / "db"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._min_confidence = float(os.getenv("OMINI_MEMORY_MIN_CONFIDENCE_FOR_SEMANTIC_RECALL", "0.6") or 0.6)
        self.path = self.db_dir / "semantic.db"
        self._conn = self._connect_and_initialize(self.path)
        self._finalizer = weakref.finalize(self, self._close_quietly, self._conn)

    def _connect_and_initialize(self, preferred_path: Path) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(preferred_path, check_same_thread=False)
            self._initialize(conn)
            return conn
        except sqlite3.OperationalError:
            fallback_dir = Path(tempfile.gettempdir()) / "omni-memory-db" / sha1(str(self.root).encode("utf-8")).hexdigest()[:12]
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self.path = fallback_dir / "semantic.db"
            conn = sqlite3.connect(self.path, check_same_thread=False)
            self._initialize(conn)
            return conn

    def _initialize(self, conn: sqlite3.Connection) -> None:
        with self._lock:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_facts (
                    fact_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_value TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source_episode_ids TEXT NOT NULL,
                    goal_types TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_reinforced_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert_fact(self, fact: SemanticFact) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO semantic_facts (
                    fact_id, subject, predicate, object_value, confidence, source_episode_ids,
                    goal_types, created_at, last_reinforced_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.fact_id,
                    fact.subject,
                    fact.predicate,
                    fact.object_value,
                    fact.confidence,
                    json.dumps(fact.source_episode_ids, ensure_ascii=False),
                    json.dumps(fact.goal_types, ensure_ascii=False),
                    fact.created_at,
                    fact.last_reinforced_at,
                    json.dumps(fact.metadata, ensure_ascii=False),
                ),
            )
            self._conn.commit()

    def get_facts(self, *, subject: str, min_confidence: float | None = None, limit: int = 10) -> list[SemanticFact]:
        threshold = self._min_confidence if min_confidence is None else min_confidence
        rows = self._conn.execute(
            """
            SELECT * FROM semantic_facts
            WHERE subject = ? AND confidence >= ?
            ORDER BY confidence DESC, last_reinforced_at DESC
            LIMIT ?
            """,
            (subject, threshold, max(1, limit)),
        ).fetchall()
        return [self._row_to_fact(row) for row in rows]

    def recent(self, *, limit: int = 50) -> list[SemanticFact]:
        rows = self._conn.execute(
            "SELECT * FROM semantic_facts ORDER BY last_reinforced_at DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
        return [self._row_to_fact(row) for row in rows]

    def current_journal_mode(self) -> str:
        row = self._conn.execute("PRAGMA journal_mode").fetchone()
        return str(row[0]).lower() if row else ""

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            return

    @staticmethod
    def _close_quietly(conn: sqlite3.Connection) -> None:
        try:
            conn.close()
        except Exception:
            return

    @staticmethod
    def _row_to_fact(row: sqlite3.Row | tuple) -> SemanticFact:
        values = list(row)
        return SemanticFact(
            fact_id=str(values[0]),
            subject=str(values[1]),
            predicate=str(values[2]),
            object_value=str(values[3]),
            confidence=float(values[4]),
            source_episode_ids=[str(item) for item in json.loads(values[5] or "[]")],
            goal_types=[str(item) for item in json.loads(values[6] or "[]")],
            created_at=str(values[7]),
            last_reinforced_at=str(values[8]),
            metadata=dict(json.loads(values[9] or "{}")),
        )

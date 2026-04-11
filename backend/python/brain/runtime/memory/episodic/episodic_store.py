from __future__ import annotations

import json
import sqlite3
import threading
import tempfile
import weakref
from hashlib import sha1
from pathlib import Path

from .models import Episode


class EpisodicStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.db_dir = root / ".logs" / "fusion-runtime" / "memory" / "db"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.path = self.db_dir / "episodic.db"
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
            self.path = fallback_dir / "episodic.db"
            conn = sqlite3.connect(self.path, check_same_thread=False)
            self._initialize(conn)
            return conn

    def _initialize(self, conn: sqlite3.Connection) -> None:
        with self._lock:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    subgoal_id TEXT,
                    session_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    progress_at_start REAL NOT NULL,
                    progress_at_end REAL NOT NULL,
                    constraints_active TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_episode(self, episode: Episode) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO episodes (
                    episode_id, goal_id, subgoal_id, session_id, description, event_type, outcome,
                    progress_at_start, progress_at_end, constraints_active, evidence_ids,
                    duration_seconds, created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode.episode_id,
                    episode.goal_id,
                    episode.subgoal_id,
                    episode.session_id,
                    episode.description,
                    episode.event_type,
                    episode.outcome,
                    episode.progress_at_start,
                    episode.progress_at_end,
                    json.dumps(episode.constraints_active, ensure_ascii=False),
                    json.dumps(episode.evidence_ids, ensure_ascii=False),
                    episode.duration_seconds,
                    episode.created_at,
                    json.dumps(episode.metadata, ensure_ascii=False),
                ),
            )
            self._conn.commit()

    def query_by_goal(self, goal_id: str, *, limit: int = 20) -> list[Episode]:
        rows = self._conn.execute(
            "SELECT * FROM episodes WHERE goal_id = ? ORDER BY created_at DESC LIMIT ?",
            (goal_id, max(1, limit)),
        ).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def query_by_outcome(self, outcome: str, *, limit: int = 20) -> list[Episode]:
        rows = self._conn.execute(
            "SELECT * FROM episodes WHERE outcome = ? ORDER BY created_at DESC LIMIT ?",
            (outcome, max(1, limit)),
        ).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def query_similar_context(
        self,
        *,
        event_type: str,
        progress_min: float,
        progress_max: float,
        limit: int = 5,
    ) -> list[Episode]:
        rows = self._conn.execute(
            """
            SELECT * FROM episodes
            WHERE event_type = ?
              AND progress_at_end >= ?
              AND progress_at_start <= ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (event_type, progress_min, progress_max, max(1, limit)),
        ).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def recent(self, *, limit: int = 50) -> list[Episode]:
        rows = self._conn.execute(
            "SELECT * FROM episodes ORDER BY created_at DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
        return [self._row_to_episode(row) for row in rows]

    def current_journal_mode(self) -> str:
        row = self._conn.execute("PRAGMA journal_mode").fetchone()
        return str(row[0]).lower() if row else ""

    def current_synchronous_mode(self) -> int:
        row = self._conn.execute("PRAGMA synchronous").fetchone()
        return int(row[0]) if row else -1

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
    def _row_to_episode(row: sqlite3.Row | tuple) -> Episode:
        values = list(row)
        return Episode(
            episode_id=str(values[0]),
            goal_id=str(values[1]),
            subgoal_id=str(values[2]) if values[2] else None,
            session_id=str(values[3]),
            description=str(values[4]),
            event_type=str(values[5]),
            outcome=str(values[6]),
            progress_at_start=float(values[7]),
            progress_at_end=float(values[8]),
            constraints_active=[str(item) for item in json.loads(values[9] or "[]")],
            evidence_ids=[str(item) for item in json.loads(values[10] or "[]")],
            duration_seconds=float(values[11]),
            created_at=str(values[12]),
            metadata=dict(json.loads(values[13] or "{}")),
        )

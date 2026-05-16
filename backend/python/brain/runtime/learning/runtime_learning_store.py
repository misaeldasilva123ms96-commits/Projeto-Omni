from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brain.runtime.observability._reader_utils import read_tail_jsonl


class RuntimeLearningStore:
    """Append-only bounded persistence for Phase 34 turn records (same tree as LearningStore evidence)."""

    def __init__(self, root: Path) -> None:
        self._path = root / ".logs" / "fusion-runtime" / "learning" / "evidence" / "runtime_turn_records.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append_record(self, record: dict[str, Any]) -> bool:
        try:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")
            return True
        except OSError:
            return False

    def read_latest_record(self) -> dict[str, Any] | None:
        """Return the most recent Phase 34 runtime learning record, if any."""
        if not self._path.exists():
            return None
        for payload in reversed(read_tail_jsonl(self._path, limit=1)):
            return payload
        return None

    def read_recent_for_session(self, session_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
        """Most recent learning records for a session (newest first)."""
        sid = str(session_id or "").strip()
        if not sid or limit <= 0:
            return []
        if not self._path.exists():
            return []
        out: list[dict[str, Any]] = []
        tail_scan_limit = max(64, int(limit) * 20)
        for payload in reversed(read_tail_jsonl(self._path, limit=tail_scan_limit)):
            if str(payload.get("session_id", "")).strip() != sid:
                continue
            out.append(payload)
            if len(out) >= limit:
                break
        return out

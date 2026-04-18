from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from brain.runtime.experience.experience_models import ExperienceRecord


class ExperienceStore:
    """Append-only canonical experience records (Phase 41.1)."""

    def __init__(self, root: Path) -> None:
        self._path = root / ".logs" / "fusion-runtime" / "experience" / "experience_records.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: ExperienceRecord) -> bool:
        try:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record.as_dict(), ensure_ascii=False))
                handle.write("\n")
            return True
        except OSError:
            return False

    def read_recent_for_session(self, session_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        sid = str(session_id or "").strip()
        if not sid or limit <= 0:
            return []
        if not self._path.exists():
            return []
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for line in reversed(text.splitlines()):
            raw = line.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if str(row.get("session_id", "")).strip() != sid:
                continue
            out.append(row)
            if len(out) >= limit:
                break
        return out

    def session_record_count(self, session_id: str) -> int:
        return len(self.read_recent_for_session(session_id, limit=50_000))

    def snapshot_counts(self, *, session_limit: int = 12) -> dict[str, Any]:
        """Safe aggregate for observability (no row bodies)."""
        if not self._path.exists():
            return {"total_lines": 0, "sessions_touched": 0, "top_sessions": []}
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return {"total_lines": 0, "sessions_touched": 0, "top_sessions": []}
        lines = [ln for ln in text.splitlines() if ln.strip()]
        c = Counter()
        for raw in lines[-2000:]:
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("session_id"):
                c[str(row["session_id"]).strip()[:64]] += 1
        top = [{"session_id": sid, "count": n} for sid, n in c.most_common(session_limit)]
        return {"total_lines": len(lines), "sessions_touched": len(c), "top_sessions": top}

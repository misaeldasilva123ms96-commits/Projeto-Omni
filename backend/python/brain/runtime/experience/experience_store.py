from __future__ import annotations

import json
from collections import Counter
from collections import deque
from pathlib import Path
from typing import Any

from brain.runtime.experience.experience_models import ExperienceRecord


JSONL_TAIL_MAX_BYTES = 2 * 1024 * 1024


def _read_tail_jsonl(path: Path, *, limit: int, chunk_size: int = 8192, max_bytes: int = JSONL_TAIL_MAX_BYTES) -> list[dict[str, Any]]:
    if limit <= 0 or not path.exists():
        return []
    collected = bytearray()
    bytes_read = 0
    newline_target = max(8, limit * 3)
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell()
            while position > 0 and bytes_read < max_bytes:
                step = min(chunk_size, position, max_bytes - bytes_read)
                position -= step
                handle.seek(position)
                collected = bytearray(handle.read(step)) + collected
                bytes_read += step
                if collected.count(b"\n") >= newline_target:
                    break
    except OSError:
        return []
    results: deque[dict[str, Any]] = deque(maxlen=max(1, limit))
    for raw_line in collected.decode("utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            results.append(payload)
    return list(results)


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
        scan_limit = max(64, int(limit) * 8)
        out: list[dict[str, Any]] = []
        for row in reversed(_read_tail_jsonl(self._path, limit=scan_limit)):
            if str(row.get("session_id", "")).strip() != sid:
                continue
            out.append(row)
            if len(out) >= limit:
                break
        return out

    def session_record_count(self, session_id: str) -> int:
        sid = str(session_id or "").strip()
        if not sid or not self._path.exists():
            return 0
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return 0
        count = 0
        for raw in text.splitlines():
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and str(row.get("session_id", "")).strip() == sid:
                count += 1
        return count

    def read_recent_global(self, *, limit: int = 200) -> list[dict[str, Any]]:
        """Most recent experience rows (any session), newest first — bounded for observability."""
        if limit <= 0:
            return []
        return list(reversed(_read_tail_jsonl(self._path, limit=limit)))

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

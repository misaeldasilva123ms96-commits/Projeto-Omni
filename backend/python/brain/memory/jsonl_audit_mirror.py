from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .memory_models import redact_payload


class JSONLAuditMirror:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record_type: str, payload: dict[str, Any]) -> None:
        redacted = redact_payload(payload)
        line = json.dumps(
            {"type": record_type, "payload": redacted},
            ensure_ascii=False,
        )
        with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.write("\n")

    def read_all(self, limit: int = 0) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self._lock:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        records.append(json.loads(stripped))
                    except json.JSONDecodeError:
                        continue
                    if limit > 0 and len(records) >= limit:
                        break
        return records

    def count_lines(self) -> int:
        if not self._path.exists():
            return 0
        with self._lock:
            with self._path.open("r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())

    def truncate(self) -> None:
        with self._lock:
            self._path.write_text("", encoding="utf-8")

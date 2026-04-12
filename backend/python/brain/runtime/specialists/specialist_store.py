from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import CoordinationTrace


class SpecialistStore:
    CANONICAL_LOG_NAME = "coordination_log.jsonl"

    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "specialists"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / self.CANONICAL_LOG_NAME
        self._lock = threading.RLock()

    def append_trace(self, trace: CoordinationTrace) -> None:
        with self._lock:
            try:
                payload = trace.as_dict()
                if not payload.get("trace_id"):
                    return
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            except Exception:
                return

    def load_recent(self, *, limit: int = 20) -> list[dict]:
        with self._lock:
            if not self.path.exists():
                return []
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except Exception:
                return []
        results: list[dict] = []
        for line in lines[-max(1, limit):]:
            try:
                payload = json.loads(line)
            except Exception:
                continue
            if isinstance(payload, dict):
                results.append(payload)
        return results

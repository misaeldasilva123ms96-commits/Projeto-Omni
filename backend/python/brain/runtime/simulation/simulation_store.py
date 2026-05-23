from __future__ import annotations

import json
from pathlib import Path

from brain.runtime.observability._reader_utils import read_tail_jsonl

from .models import SimulationResult


JSONL_TAIL_MAX_BYTES = 2 * 1024 * 1024


class SimulationStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.base_dir = root / ".logs" / "fusion-runtime" / "simulation"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "simulation_log.jsonl"

    def append(self, result: SimulationResult) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result.as_dict(), ensure_ascii=False))
                handle.write("\n")
        except Exception:
            return

    def load_recent(self, *, limit: int = 10) -> list[dict[str, object]]:
        return read_tail_jsonl(self.path, limit=max(1, limit), max_bytes=JSONL_TAIL_MAX_BYTES)

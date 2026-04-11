from __future__ import annotations

import json
from pathlib import Path

from .models import SimulationResult


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
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        payloads: list[dict[str, object]] = []
        for line in lines[-max(1, limit):]:
            if not line.strip():
                continue
            try:
                payloads.append(json.loads(line))
            except Exception:
                continue
        return payloads

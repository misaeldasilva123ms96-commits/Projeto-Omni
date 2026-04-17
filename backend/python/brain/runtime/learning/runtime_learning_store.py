from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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

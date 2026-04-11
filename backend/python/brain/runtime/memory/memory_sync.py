from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


class MemorySync:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.base_dir = root / ".logs" / "fusion-runtime" / "memory"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.export_path = self.base_dir / "sync-export.jsonl"
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="omni-memory-sync")

    def export_async(self, *, payload: dict[str, Any]) -> None:
        self._executor.submit(self._safe_write, payload)

    def _safe_write(self, payload: dict[str, Any]) -> None:
        try:
            with self.export_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False))
                handle.write("\n")
        except Exception:
            return

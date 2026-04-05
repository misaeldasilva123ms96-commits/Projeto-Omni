from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CheckpointStore:
    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "checkpoints"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.base_dir / f"{run_id}.json"

    def save(self, run_id: str, payload: dict[str, Any]) -> Path:
        path = self._path(run_id)
        record = {
            **payload,
            "run_id": run_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, run_id: str) -> dict[str, Any]:
        path = self._path(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, run_id: str) -> bool:
        return self._path(run_id).exists()

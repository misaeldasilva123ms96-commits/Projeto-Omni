from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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
        created_at = payload.get("created_at")
        updated_at = payload.get("updated_at")
        record = {
            **payload,
            "run_id": run_id,
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
            "updated_at": updated_at or datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, run_id: str) -> dict[str, Any]:
        path = self._path(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, run_id: str) -> bool:
        return self._path(run_id).exists()

    def validate(
        self,
        run_id: str,
        *,
        stale_after_minutes: int = 120,
        expected_plan_signature: str | None = None,
    ) -> dict[str, Any]:
        payload = self.load(run_id)
        updated_at = payload.get("updated_at")
        stale = False
        if updated_at:
            try:
                updated_dt = datetime.fromisoformat(str(updated_at))
                stale = updated_dt < datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
            except ValueError:
                stale = True
        signature = str(payload.get("plan_signature", ""))
        signature_mismatch = bool(expected_plan_signature and signature and signature != expected_plan_signature)
        return {
            "ok": not stale and not signature_mismatch,
            "stale": stale,
            "signature_mismatch": signature_mismatch,
            "payload": payload,
        }

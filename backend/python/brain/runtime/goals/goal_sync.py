from __future__ import annotations

import asyncio
import json
from pathlib import Path

from .models import Goal


class GoalSync:
    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "goals"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.export_path = self.base_dir / "goal_sync_export.jsonl"

    async def export_goal(self, goal: Goal) -> bool:
        try:
            await asyncio.to_thread(self._append_payload, goal.as_dict())
            return True
        except Exception:
            return False

    async def export_batch(self, goals: list[Goal]) -> bool:
        try:
            await asyncio.to_thread(self._append_batch, [goal.as_dict() for goal in goals])
            return True
        except Exception:
            return False

    def _append_payload(self, payload: dict[str, object]) -> None:
        with self.export_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")

    def _append_batch(self, payloads: list[dict[str, object]]) -> None:
        with self.export_path.open("a", encoding="utf-8") as handle:
            for payload in payloads:
                handle.write(json.dumps(payload, ensure_ascii=False))
                handle.write("\n")

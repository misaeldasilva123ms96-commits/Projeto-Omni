from __future__ import annotations

from typing import Any

from .models import PlanCheckpoint, TaskPlan, utc_now_iso
from .task_state_store import TaskStateStore


class CheckpointManager:
    def __init__(self, store: TaskStateStore) -> None:
        self.store = store

    def create_checkpoint(
        self,
        *,
        plan: TaskPlan,
        step_id: str | None,
        snapshot_summary: str,
        resumable_state_payload: dict[str, Any],
        last_outcome_summary: str,
    ) -> PlanCheckpoint:
        checkpoint = PlanCheckpoint.build(
            plan_id=plan.plan_id,
            step_id=step_id,
            snapshot_summary=snapshot_summary,
            resumable_state_payload=self._compact_payload(resumable_state_payload),
            last_outcome_summary=last_outcome_summary[:400],
        )
        plan.checkpoint_pointer = checkpoint.checkpoint_id
        plan.updated_at = utc_now_iso()
        self.store.append_checkpoint(checkpoint)
        self.store.save_plan(plan)
        return checkpoint

    def _compact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        compact: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, str):
                compact[key] = value[:400]
            elif isinstance(value, list):
                compact[key] = value[:8]
            elif isinstance(value, dict):
                compact[key] = {inner_key: self._compact_scalar(inner_value) for inner_key, inner_value in list(value.items())[:12]}
            else:
                compact[key] = value
        return compact

    @staticmethod
    def _compact_scalar(value: Any) -> Any:
        if isinstance(value, str):
            return value[:240]
        if isinstance(value, list):
            return value[:5]
        if isinstance(value, dict):
            return {key: str(inner)[:120] for key, inner in list(value.items())[:8]}
        return value

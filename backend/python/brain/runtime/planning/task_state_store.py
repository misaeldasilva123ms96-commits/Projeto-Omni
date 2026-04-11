from __future__ import annotations

import json
from pathlib import Path

from .models import OperationalSummary, PlanCheckpoint, TaskPlan


class TaskStateStore:
    def __init__(self, root: Path) -> None:
        self.base_dir = root / ".logs" / "fusion-runtime" / "planning"
        self.plans_dir = self.base_dir / "plans"
        self.checkpoints_dir = self.base_dir / "checkpoints"
        self.summaries_dir = self.base_dir / "summaries"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

    def _plan_path(self, plan_id: str) -> Path:
        return self.plans_dir / f"{plan_id}.json"

    def _checkpoint_path(self, plan_id: str) -> Path:
        return self.checkpoints_dir / f"{plan_id}.jsonl"

    def _summary_path(self, plan_id: str) -> Path:
        return self.summaries_dir / f"{plan_id}.json"

    def save_plan(self, plan: TaskPlan) -> None:
        self._plan_path(plan.plan_id).write_text(
            json.dumps(plan.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_plan(self, plan_id: str) -> TaskPlan | None:
        path = self._plan_path(plan_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return TaskPlan.from_dict(payload)

    def append_checkpoint(self, checkpoint: PlanCheckpoint) -> None:
        path = self._checkpoint_path(checkpoint.plan_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(checkpoint.as_dict(), ensure_ascii=False))
            handle.write("\n")

    def load_checkpoints(self, plan_id: str) -> list[PlanCheckpoint]:
        path = self._checkpoint_path(plan_id)
        if not path.exists():
            return []
        checkpoints: list[PlanCheckpoint] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue
            if isinstance(payload, dict):
                checkpoints.append(PlanCheckpoint.from_dict(payload))
        return checkpoints

    def load_latest_checkpoint(self, plan_id: str) -> PlanCheckpoint | None:
        checkpoints = self.load_checkpoints(plan_id)
        return checkpoints[-1] if checkpoints else None

    def list_recent_plans(self, limit: int = 10) -> list[TaskPlan]:
        plans: list[TaskPlan] = []
        for path in self.plans_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                plans.append(TaskPlan.from_dict(payload))
        plans.sort(key=lambda item: item.updated_at, reverse=True)
        return plans[:limit]

    def load_latest_active_plan(self, session_id: str, task_id: str | None = None) -> TaskPlan | None:
        for plan in self.list_recent_plans(limit=50):
            if plan.session_id != session_id:
                continue
            if task_id and plan.task_id != task_id:
                continue
            if plan.status.value in {"created", "active", "paused", "blocked"}:
                return plan
        return None

    def find_plan(self, *, session_id: str, task_id: str, run_id: str | None) -> TaskPlan | None:
        for plan in self.list_recent_plans(limit=100):
            if plan.session_id != session_id or plan.task_id != task_id:
                continue
            if run_id and plan.run_id == run_id:
                return plan
        return None

    def save_summary(self, summary: OperationalSummary) -> None:
        self._summary_path(summary.plan_id).write_text(
            json.dumps(summary.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_summary(self, plan_id: str) -> OperationalSummary | None:
        path = self._summary_path(plan_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return OperationalSummary.from_dict(payload)

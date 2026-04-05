from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths
from brain.runtime.service_contracts import build_task_envelope, build_task_status, validate_start_task_request


class TaskService:
    def __init__(self, entrypoint: Path) -> None:
        self.orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(entrypoint))

    def execute_task(self, *, user_id: str, session_id: str, message: str) -> dict[str, Any]:
        previous_session = os.environ.get("AI_SESSION_ID")
        request = validate_start_task_request(user_id=user_id, session_id=session_id, message=message)
        task_id = f"task-{request['user_id']}-{request['session_id']}"
        try:
            os.environ["AI_SESSION_ID"] = request["session_id"]
            response = self.orchestrator.run(request["message"])
            return build_task_envelope(
                user_id=request["user_id"],
                session_id=request["session_id"],
                task_id=task_id,
                response=response,
            )
        finally:
            if previous_session is None:
                os.environ.pop("AI_SESSION_ID", None)
            else:
                os.environ["AI_SESSION_ID"] = previous_session

    def resume_task(self, *, run_id: str) -> dict[str, Any]:
        return self.orchestrator.resume_run(run_id)

    def inspect_run(self, *, run_id: str) -> dict[str, Any]:
        return self.orchestrator.checkpoint_store.load(run_id)

    def inspect_plan_hierarchy(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return {
            "run_id": run_id,
            "task_id": checkpoint.get("task_id"),
            "plan_hierarchy": checkpoint.get("plan_hierarchy"),
            "plan_graph": checkpoint.get("plan_graph"),
            "branch_state": checkpoint.get("branch_state"),
            "execution_tree": checkpoint.get("execution_tree"),
        }

    def inspect_learning_memory(self) -> dict[str, Any]:
        learning_path = self.orchestrator.paths.root / ".logs" / "fusion-runtime" / "execution-learning-memory.json"
        if not learning_path.exists():
            return {"entries": []}
        import json

        return json.loads(learning_path.read_text(encoding="utf-8"))

    def inspect_reflection(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return {
            "run_id": run_id,
            "reflection_summary": checkpoint.get("reflection_summary"),
        }

    def inspect_branches(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return {
            "run_id": run_id,
            "branch_state": checkpoint.get("branch_state"),
            "simulation_summary": checkpoint.get("simulation_summary"),
        }

    def inspect_simulation(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return {
            "run_id": run_id,
            "simulation_summary": checkpoint.get("simulation_summary"),
            "policy_summary": checkpoint.get("policy_summary"),
        }

    def inspect_contributions(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return {
            "run_id": run_id,
            "cooperative_plan": checkpoint.get("cooperative_plan"),
            "strategy_suggestions": checkpoint.get("strategy_suggestions", []),
            "negotiation_summary": checkpoint.get("negotiation_summary"),
        }

    def inspect_negotiation(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return {
            "run_id": run_id,
            "negotiation_summary": checkpoint.get("negotiation_summary"),
        }

    def inspect_execution_state(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return {
            "run_id": run_id,
            "execution_tree": checkpoint.get("execution_tree"),
            "branch_state": checkpoint.get("branch_state"),
            "strategy_optimization": checkpoint.get("strategy_optimization"),
        }

    def inspect_supervision(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return {
            "run_id": run_id,
            "supervision": checkpoint.get("supervision"),
        }

    def inspect_run_intelligence(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        run_summary_path = self.orchestrator.paths.root / ".logs" / "fusion-runtime" / "run-summaries.jsonl"
        latest_summary = None
        if run_summary_path.exists():
            import json

            for line in reversed(run_summary_path.read_text(encoding="utf-8").splitlines()):
                if not line.strip():
                    continue
                candidate = json.loads(line)
                if candidate.get("run_id") == run_id:
                    latest_summary = candidate
                    break
        return {
            "run_id": run_id,
            "checkpoint": checkpoint,
            "run_summary": latest_summary,
        }

    def task_status(self, *, run_id: str) -> dict[str, Any]:
        checkpoint = self.orchestrator.checkpoint_store.load(run_id)
        return build_task_status(run_id=run_id, checkpoint=checkpoint)

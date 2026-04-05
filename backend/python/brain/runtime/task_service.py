from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from brain.runtime.orchestrator import BrainOrchestrator, BrainPaths


class TaskService:
    def __init__(self, entrypoint: Path) -> None:
        self.orchestrator = BrainOrchestrator(BrainPaths.from_entrypoint(entrypoint))

    def execute_task(self, *, user_id: str, session_id: str, message: str) -> dict[str, Any]:
        previous_session = os.environ.get("AI_SESSION_ID")
        try:
            os.environ["AI_SESSION_ID"] = session_id
            response = self.orchestrator.run(message)
            return {
                "user_id": user_id,
                "session_id": session_id,
                "response": response,
            }
        finally:
            if previous_session is None:
                os.environ.pop("AI_SESSION_ID", None)
            else:
                os.environ["AI_SESSION_ID"] = previous_session

    def resume_task(self, *, run_id: str) -> dict[str, Any]:
        return self.orchestrator.resume_run(run_id)

    def inspect_run(self, *, run_id: str) -> dict[str, Any]:
        return self.orchestrator.checkpoint_store.load(run_id)

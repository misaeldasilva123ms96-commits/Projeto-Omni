"""Fusion / run terminal completion vs failure (Phase 30.10 decomposition)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from brain.runtime.control import GovernanceResolutionController, RunStatus

from .run_lifecycle_service import RunLifecycleService


class CompletionService:
    __slots__ = ("_get_controller", "_progress_fn", "_run_lifecycle")

    def __init__(
        self,
        *,
        get_controller: Callable[[], GovernanceResolutionController | None],
        run_lifecycle: RunLifecycleService,
        progress_fn: Callable[[list[dict[str, Any]]], float],
    ) -> None:
        self._get_controller = get_controller
        self._run_lifecycle = run_lifecycle
        self._progress_fn = progress_fn

    def apply_fusion_terminal_status(
        self,
        *,
        run_id: str,
        step_results: list[dict[str, Any]],
    ) -> None:
        ctrl = self._get_controller()
        if ctrl is not None:
            if step_results and all(item.get("ok") for item in step_results):
                ctrl.handle_completion(
                    run_id=run_id,
                    last_action="goal_completed",
                    progress=1.0,
                )
            else:
                ctrl.handle_failure(
                    run_id=run_id,
                    last_action="goal_failed",
                    progress=self._progress_fn(step_results),
                    reason=None,
                )
        else:
            self._run_lifecycle.update_run_status(
                run_id=run_id,
                status=RunStatus.COMPLETED if step_results and all(item.get("ok") for item in step_results) else RunStatus.FAILED,
                last_action="goal_completed" if step_results and all(item.get("ok") for item in step_results) else "goal_failed",
                progress_score=1.0 if step_results and all(item.get("ok") for item in step_results) else self._progress_fn(step_results),
            )

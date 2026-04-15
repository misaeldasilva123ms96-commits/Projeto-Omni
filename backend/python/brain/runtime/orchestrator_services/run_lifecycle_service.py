"""Run registration and status updates (Phase 30.10 decomposition)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from brain.runtime.control import GovernanceResolutionController, RunRecord, RunRegistry, RunStatus


class RunLifecycleService:
    __slots__ = ("_get_controller", "_run_registry")

    def __init__(
        self,
        *,
        run_registry: RunRegistry | None,
        get_controller: Callable[[], GovernanceResolutionController | None],
    ) -> None:
        self._run_registry = run_registry
        self._get_controller = get_controller

    def register_run_start(
        self,
        *,
        run_id: str,
        session_id: str,
        goal_id: str | None,
        status: RunStatus,
        last_action: str,
        progress_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            if self._run_registry is None:
                return
            ctrl = self._get_controller()
            if ctrl is not None:
                ctrl.register_run_start(
                    run_id=run_id,
                    goal_id=goal_id,
                    session_id=session_id,
                    status=status,
                    last_action=last_action,
                    progress_score=progress_score,
                    metadata=metadata,
                )
                return
            run = self._run_registry.register(
                RunRecord.build(
                    run_id=run_id,
                    goal_id=goal_id,
                    session_id=session_id,
                    status=status,
                    last_action=last_action,
                    progress_score=progress_score,
                    metadata=metadata,
                )
            )
            run.transition_resolution(
                status=status,
                last_action=last_action,
                decision_source="runtime_orchestrator",
                engine_mode=str((metadata or {}).get("engine_mode", "")).strip() or None,
                promotion_metadata=dict((metadata or {}).get("promotion_metadata", {}) or {}),
            )
            self._run_registry.flush()
        except Exception:
            return

    def update_run_status(
        self,
        *,
        run_id: str,
        status: RunStatus,
        last_action: str,
        progress_score: float,
    ) -> None:
        try:
            if self._run_registry is None:
                return
            decision_source = "operator_control" if str(last_action).startswith("operator_") else "runtime_orchestrator"
            operator_id = "supabase_user" if decision_source == "operator_control" else None
            ctrl = self._get_controller()
            if ctrl is not None:
                ctrl.transition_run(
                    run_id=run_id,
                    status=status,
                    last_action=last_action,
                    progress=progress_score,
                    reason=None,
                    decision_source=decision_source,
                    operator_id=operator_id,
                )
                return
            self._run_registry.update_status(
                run_id=run_id,
                status=status,
                last_action=last_action,
                progress=progress_score,
                decision_source=decision_source,
                operator_id=operator_id,
            )
        except Exception:
            return

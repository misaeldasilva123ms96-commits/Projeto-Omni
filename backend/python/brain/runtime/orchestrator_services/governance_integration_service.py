"""Orchestrator-facing governance integration (Phase 30.10 decomposition)."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from brain.runtime.control import GovernanceResolutionController, RunRegistry, RunStatus
from brain.runtime.control.governance_wait import (
    GovernanceWaitTick,
    bounded_governance_poll,
    clamp_governance_poll_interval_seconds,
)

from .run_lifecycle_service import RunLifecycleService


def _run_control_poll_interval_seconds() -> float:
    raw = str(os.getenv("OMINI_RUN_CONTROL_POLL_SECONDS", "2") or "2").strip()
    try:
        return clamp_governance_poll_interval_seconds(float(raw))
    except ValueError:
        return clamp_governance_poll_interval_seconds(2.0)


def _run_control_max_wait_seconds() -> float:
    raw = str(os.getenv("OMINI_RUN_CONTROL_MAX_WAIT_SECONDS", "300") or "300").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 300.0


class GovernanceIntegrationService:
    __slots__ = ("_get_controller", "_run_lifecycle", "_run_registry")

    def __init__(
        self,
        *,
        run_registry: RunRegistry | None,
        get_controller: Callable[[], GovernanceResolutionController | None],
        run_lifecycle: RunLifecycleService,
    ) -> None:
        self._run_registry = run_registry
        self._get_controller = get_controller
        self._run_lifecycle = run_lifecycle

    def _apply_operator_timeout(self, *, run_id: str, progress_score: float) -> dict[str, Any]:
        ctrl = self._get_controller()
        if ctrl is not None:
            ctrl.handle_timeout(run_id=run_id, progress=progress_score)
        else:
            self._run_lifecycle.update_run_status(
                run_id=run_id,
                status=RunStatus.FAILED,
                last_action="operator_timeout",
                progress_score=progress_score,
            )
        return {
            "status": "failed",
            "error": "operator_timeout",
            "progress_score": progress_score,
        }

    def apply_governance_hold_after_specialist(self, *, run_id: str, progress_score: float) -> None:
        ctrl = self._get_controller()
        if ctrl is not None:
            ctrl.handle_governance_hold(run_id=run_id, progress=progress_score)
        else:
            self._run_lifecycle.update_run_status(
                run_id=run_id,
                status=RunStatus.AWAITING_APPROVAL,
                last_action="governance_hold",
                progress_score=progress_score,
            )

    def await_run_control_clearance(self, *, run_id: str) -> dict[str, Any]:
        if self._run_registry is None:
            return {"status": "running"}
        poll_interval = _run_control_poll_interval_seconds()
        max_wait = _run_control_max_wait_seconds()

        def tick(_attempt: int, elapsed: float) -> GovernanceWaitTick:
            try:
                self._run_registry.reload_from_disk()
                record = self._run_registry.get(run_id)
            except Exception:
                return GovernanceWaitTick({"status": "running"})
            if record is None or record.status == RunStatus.RUNNING:
                return GovernanceWaitTick({"status": "running"})
            control_enabled = bool((record.metadata or {}).get("operator_control_enabled"))
            if not control_enabled:
                return GovernanceWaitTick({"status": "running"})
            should_wait = record.status == RunStatus.AWAITING_APPROVAL or (
                record.status == RunStatus.PAUSED and str(record.last_action).startswith("operator_")
            )
            if not should_wait:
                return GovernanceWaitTick({"status": record.status.value, "progress_score": record.progress_score})
            if elapsed >= max_wait:
                return GovernanceWaitTick(
                    self._apply_operator_timeout(run_id=run_id, progress_score=record.progress_score)
                )
            return GovernanceWaitTick(None)

        def on_deadline_exceeded() -> dict[str, Any]:
            try:
                self._run_registry.reload_from_disk()
                record = self._run_registry.get(run_id)
            except Exception:
                return {"status": "running"}
            if record is None or record.status == RunStatus.RUNNING:
                return {"status": "running"}
            control_enabled = bool((record.metadata or {}).get("operator_control_enabled"))
            if not control_enabled:
                return {"status": "running"}
            should_wait = record.status == RunStatus.AWAITING_APPROVAL or (
                record.status == RunStatus.PAUSED and str(record.last_action).startswith("operator_")
            )
            if not should_wait:
                return {"status": record.status.value, "progress_score": record.progress_score}
            return self._apply_operator_timeout(run_id=run_id, progress_score=record.progress_score)

        poll = bounded_governance_poll(
            tick=tick,
            timeout_seconds=max_wait,
            poll_interval_seconds=poll_interval,
            on_deadline_exceeded=on_deadline_exceeded,
        )
        return poll.payload

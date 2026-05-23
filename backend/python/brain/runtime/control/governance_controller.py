"""Central governance-aware resolution transitions (Phase 30.7)."""

from __future__ import annotations

from typing import Any

from .governance_taxonomy import GovernanceReason, build_governance_decision, map_legacy_reason_string
from .governance_timeline import infer_event_type_from_transition
from .run_registry import RunRecord, RunRegistry, RunStatus, infer_reason_from_action, infer_resolution_state


class GovernanceResolutionController:
    """Canonical coordinator for run status + resolution + governance timeline updates."""

    __slots__ = ("_registry",)

    def __init__(self, registry: RunRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> RunRegistry:
        return self._registry

    def preview_transition(
        self,
        record: RunRecord,
        *,
        status: RunStatus,
        last_action: str,
        reason: str | None,
        decision_source: str,
    ) -> dict[str, Any]:
        """Describe governance fields after a hypothetical transition (non-mutating)."""
        fallback = infer_reason_from_action(last_action, status=status)
        normalized = map_legacy_reason_string(str(reason or ""), fallback=fallback)
        next_state = infer_resolution_state(status, normalized)
        prev = record.resolution.current_resolution if record.resolution else next_state.value
        gov = build_governance_decision(reason=normalized.value, decision_source=decision_source)
        event_type = infer_event_type_from_transition(
            reason=normalized.value,
            run_status=status.value,
            current_resolution=next_state.value,
            previous_resolution=prev,
        )
        return {
            "event_type": event_type,
            "resolution": next_state.value,
            "previous_resolution": prev,
            "governance": gov.as_dict(),
        }

    def transition_run(
        self,
        *,
        run_id: str,
        status: RunStatus,
        last_action: str,
        progress: float,
        reason: str | None = None,
        decision_source: str = "runtime_orchestrator",
        operator_id: str | None = None,
        promotion_metadata: dict[str, Any] | None = None,
        engine_mode: str | None = None,
    ) -> RunRecord | None:
        """Apply a governance-aware status transition through the registry."""
        return self._registry.update_status(
            run_id=run_id,
            status=status,
            last_action=last_action,
            progress=progress,
            reason=reason,
            decision_source=decision_source,
            operator_id=operator_id,
            promotion_metadata=promotion_metadata,
            engine_mode=engine_mode,
        )

    def apply_transition(
        self,
        *,
        run_id: str,
        status: RunStatus,
        last_action: str,
        progress: float,
        reason: str | None = None,
        decision_source: str = "runtime_orchestrator",
        operator_id: str | None = None,
        promotion_metadata: dict[str, Any] | None = None,
        engine_mode: str | None = None,
    ) -> RunRecord | None:
        """Alias for ``transition_run`` (canonical verb per convergence program)."""
        return self.transition_run(
            run_id=run_id,
            status=status,
            last_action=last_action,
            progress=progress,
            reason=reason,
            decision_source=decision_source,
            operator_id=operator_id,
            promotion_metadata=promotion_metadata,
            engine_mode=engine_mode,
        )

    def register_run_start(
        self,
        *,
        run_id: str,
        goal_id: str | None,
        session_id: str,
        status: RunStatus,
        last_action: str,
        progress_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> RunRecord | None:
        """
        Persist a new or merged run row with initial resolution and a single ``start`` timeline event.

        Does not emit a follow-up transition for the same action (avoids duplicate startup timeline rows).
        """
        run = RunRecord.build(
            run_id=run_id,
            goal_id=goal_id,
            session_id=session_id,
            status=status,
            last_action=last_action,
            progress_score=progress_score,
            metadata=metadata,
        )
        return self._registry.register(run)

    def handle_operator_action(
        self,
        *,
        run_id: str,
        action: str,
        progress: float,
        decision_source: str = "operator_cli",
        operator_id: str | None = "supabase_user",
    ) -> RunRecord | None:
        status_map = {
            "pause": RunStatus.PAUSED,
            "resume": RunStatus.RUNNING,
            "approve": RunStatus.RUNNING,
        }
        reason_map = {
            "pause": GovernanceReason.OPERATOR_PAUSE.value,
            "resume": GovernanceReason.OPERATOR_RESUME.value,
            "approve": GovernanceReason.OPERATOR_APPROVE.value,
        }
        key = str(action or "").strip().lower()
        if key not in status_map:
            raise ValueError(f"unknown operator action: {action!r}")
        last_action = f"operator_{key}"
        return self.transition_run(
            run_id=run_id,
            status=status_map[key],
            last_action=last_action,
            progress=progress,
            reason=reason_map[key],
            decision_source=decision_source,
            operator_id=operator_id,
        )

    def handle_timeout(self, *, run_id: str, progress: float) -> RunRecord | None:
        return self.transition_run(
            run_id=run_id,
            status=RunStatus.FAILED,
            last_action="operator_timeout",
            progress=progress,
            reason=GovernanceReason.TIMEOUT.value,
            decision_source="runtime_orchestrator",
            operator_id=None,
        )

    def handle_rollback(
        self,
        *,
        run_id: str,
        progress: float,
        last_action: str = "engine_promotion_rollback",
    ) -> RunRecord | None:
        return self.transition_run(
            run_id=run_id,
            status=RunStatus.FAILED,
            last_action=last_action,
            progress=progress,
            reason=GovernanceReason.PROMOTION_ROLLBACK_THRESHOLD.value,
            decision_source="runtime_orchestrator",
            operator_id=None,
        )

    def handle_governance_hold(self, *, run_id: str, progress: float) -> RunRecord | None:
        return self.transition_run(
            run_id=run_id,
            status=RunStatus.AWAITING_APPROVAL,
            last_action="governance_hold",
            progress=progress,
            reason=GovernanceReason.GOVERNANCE_HOLD.value,
            decision_source="runtime_orchestrator",
            operator_id=None,
        )

    def handle_completion(
        self,
        *,
        run_id: str,
        last_action: str = "goal_completed",
        progress: float = 1.0,
    ) -> RunRecord | None:
        return self.transition_run(
            run_id=run_id,
            status=RunStatus.COMPLETED,
            last_action=last_action,
            progress=progress,
            reason=GovernanceReason.COMPLETED.value,
            decision_source="runtime_orchestrator",
            operator_id=None,
        )

    def handle_failure(
        self,
        *,
        run_id: str,
        last_action: str,
        progress: float,
        reason: str | None = None,
        decision_source: str = "runtime_orchestrator",
    ) -> RunRecord | None:
        return self.transition_run(
            run_id=run_id,
            status=RunStatus.FAILED,
            last_action=last_action,
            progress=progress,
            reason=reason,
            decision_source=decision_source,
            operator_id=None,
        )

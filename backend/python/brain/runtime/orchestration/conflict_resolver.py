from __future__ import annotations

from .models import ConflictResolution, OrchestrationContext, OrchestrationDecision, OrchestrationRoute


class ConflictResolver:
    def resolve(
        self,
        *,
        context: OrchestrationContext,
        decision: OrchestrationDecision,
    ) -> ConflictResolution:
        conflicts: list[str] = []
        selected_route = decision.route
        reason_code = "route_selected_without_conflict"
        reason_summary = "No conflicting orchestration hints were strong enough to change the selected route."

        signal_types = {str(signal.get("signal_type", "")).strip() for signal in context.learning_signals if isinstance(signal, dict)}
        continuation = context.continuation_decision_type

        if continuation in {"pause_plan", "escalate_failure", "complete_plan", "rebuild_plan"}:
            if signal_types:
                conflicts.append("learning_hints_present_but_continuation_is_authoritative")
            reason_code = f"{continuation}_authoritative"
            reason_summary = "Execution safety and continuation lifecycle control outrank advisory learning hints."
        elif decision.route == OrchestrationRoute.RETRY_EXECUTION and signal_types & {"discouraged_retry_pattern", "high_risk_recurrence_alert"}:
            conflicts.append("learning_discourages_retry")
            reason_code = "retry_selected_under_continuation_authority"
            reason_summary = "Retry remains selected because continuation is authoritative, but the conflict is recorded for auditability."
        elif decision.route == OrchestrationRoute.TOOL_DELEGATION and "step_template_success_hint" in signal_types:
            conflicts.append("validation_hint_preserved_alongside_tool_delegation")
            reason_code = "tool_route_with_validation_hint"
            reason_summary = "Learning hints recommend extra validation, but they do not override the bounded tool route."

        return ConflictResolution.build(
            selected_route=selected_route,
            reason_code=reason_code,
            reason_summary=reason_summary,
            conflicts=conflicts,
            metadata={
                "continuation_decision_type": continuation,
                "signal_types": sorted(signal_types),
            },
        )

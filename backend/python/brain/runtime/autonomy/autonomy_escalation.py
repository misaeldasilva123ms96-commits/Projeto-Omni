"""Escalation report model for autonomy decisions.

When the Autonomy Controller decides to escalate, an EscalationReport
captures why and what context led to the escalation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .autonomy_models import AutonomyContext, AutonomyDecision


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


ESCALATION_CATEGORIES: frozenset[str] = frozenset({
    "stagnation",
    "max_attempts",
    "distinct_strategies_failed",
    "secret_detected",
    "protected_file",
    "high_risk",
    "critical_risk",
    "unsafe_ci",
    "security_signal",
    "conflict",
    "production_action",
    "no_safe_action",
    "main_push_attempt",
    "merge_attempt",
    "cycle_limit",
})


@dataclass(slots=True)
class EscalationReport:
    report_id: str
    decision_id: str
    escalation_category: str
    reason: str
    risk_level: str
    context_summary: str
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_escalation_report(
    decision: AutonomyDecision,
    ctx: AutonomyContext,
) -> EscalationReport:
    if decision.decision.value != "ESCALATE_TO_MISAEL":
        raise ValueError(
            f"Cannot build escalation report for non-escalation decision: {decision.decision.value}"
        )

    category = _classify_escalation(ctx, decision.reason)
    ctx_count = len(decision.context_snapshot)
    ctx_summary = f"Escalation — {category}. {ctx_count} context fields evaluated."

    from uuid import uuid4

    return EscalationReport(
        report_id=str(uuid4()),
        decision_id=decision.decision_id,
        escalation_category=category,
        reason=decision.reason,
        risk_level=decision.risk_level,
        context_summary=ctx_summary,
    )


def _classify_escalation(ctx: AutonomyContext, reason: str) -> str:
    if ctx.secret_detected:
        return "secret_detected"
    if ctx.protected_file_involved:
        return "protected_file"
    if ctx.unsafe_ci_signal or ctx.security_signal:
        return "unsafe_ci" if ctx.unsafe_ci_signal else "security_signal"
    if ctx.conflict_detected:
        return "conflict"
    if ctx.production_action_required:
        return "production_action"
    if ctx.direct_main_push_attempted or ctx.merge_attempted:
        return "main_push_attempt" if ctx.direct_main_push_attempted else "merge_attempt"
    if ctx.no_safe_next_action:
        return "no_safe_action"
    if ctx.stagnation_count >= 5:
        return "stagnation"
    if ctx.distinct_errors >= 3:
        return "distinct_strategies_failed"
    if ctx.consecutive_same_error > 0:
        return "max_attempts"
    return "high_risk"

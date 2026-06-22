"""Autonomy Controller policy evaluation rules.

Evaluates a runtime AutonomyContext against policy thresholds and
returns an advisory AutonomyDecision. No autonomous execution.
"""

from __future__ import annotations

import logging
from typing import Any

from .autonomy_models import (
    ADVISORY_ONLY_DECISIONS,
    DECISION_RISK_MAP,
    DISABLED_DECISIONS,
    AutonomyContext,
    AutonomyDecision,
    DecisionType,
)

logger = logging.getLogger(__name__)

# Default config values
DEFAULT_MAX_ATTEMPTS_PER_ERROR = 5
DEFAULT_MAX_STAGNANT_ATTEMPTS = 3
DEFAULT_WARN_AFTER_STAGNATION = 3
DEFAULT_ESCALATE_AFTER_STAGNATION = 5
DEFAULT_MAX_TOTAL_PROGRESSIVE_CYCLES = 50
DEFAULT_AUTONOMY_LEVEL = "supervised"


def evaluate_policy(
    ctx: AutonomyContext,
    *,
    autonomy_level: str | None = None,
    max_attempts_per_error: int = DEFAULT_MAX_ATTEMPTS_PER_ERROR,
    max_stagnant_attempts: int = DEFAULT_MAX_STAGNANT_ATTEMPTS,
    escalate_after_stagnation: int = DEFAULT_ESCALATE_AFTER_STAGNATION,
    max_total_progressive_cycles: int = DEFAULT_MAX_TOTAL_PROGRESSIVE_CYCLES,
) -> AutonomyDecision:
    level = (autonomy_level or DEFAULT_AUTONOMY_LEVEL).strip().lower()

    if ctx.no_safe_next_action:
        return _make_decision(
            DecisionType.ABORT_SAFE,
            "No safe next action available.",
            ctx,
        )

    if ctx.direct_main_push_attempted or ctx.merge_attempted:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            "Direct main push or merge attempted.",
            ctx,
        )

    if ctx.secret_detected:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            "Secret detected during operation.",
            ctx,
        )

    if ctx.protected_file_involved:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            "Protected file involved in operation.",
            ctx,
        )

    if ctx.unsafe_ci_signal or ctx.security_signal:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            "Unsafe CI or security signal detected.",
            ctx,
        )

    if ctx.conflict_detected:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            "Conflict detected during operation.",
            ctx,
        )

    if ctx.production_action_required:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            "Production or deploy action required.",
            ctx,
        )

    if ctx.stagnation_count >= escalate_after_stagnation:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            f"Stagnation count ({ctx.stagnation_count}) exceeds escalation threshold ({escalate_after_stagnation}).",
            ctx,
        )

    if ctx.distinct_errors >= max_stagnant_attempts:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            f"{ctx.distinct_errors} distinct strategies failed on same root cause.",
            ctx,
        )

    if ctx.total_progressive_cycles >= max_total_progressive_cycles:
        return _make_decision(
            DecisionType.PAUSE,
            f"Total progressive cycles ({ctx.total_progressive_cycles}) exceeds limit ({max_total_progressive_cycles}).",
            ctx,
        )

    if ctx.consecutive_same_error > 0 and ctx.error_count >= max_attempts_per_error:
        return _make_decision(
            DecisionType.ESCALATE_TO_MISAEL,
            f"Same error repeated {ctx.error_count} times (max {max_attempts_per_error}).",
            ctx,
        )

    if _is_transient_error(ctx.error_type):
        return _make_decision(
            DecisionType.RETRY,
            f"Transient error detected: {ctx.error_type}. Advisory retry.",
            ctx,
        )

    if ctx.error_count > 0 and ctx.distinct_errors > 1:
        return _make_decision(
            DecisionType.REPLAN,
            f"Multiple distinct errors ({ctx.distinct_errors}) suggest strategy change.",
            ctx,
        )

    if ctx.error_count > 0:
        return _make_decision(
            DecisionType.RETRY,
            f"Error encountered ({ctx.error_type}). Advisory retry (attempt {ctx.error_count}).",
            ctx,
        )

    if level != "supervised":
        return _make_decision(
            DecisionType.CONTINUE,
            f"No errors. Autonomy level '{level}' allows continuation.",
            ctx,
        )

    return _make_decision(
        DecisionType.CONTINUE,
        "No errors or risk signals detected. Advisory continue.",
        ctx,
    )


def _make_decision(
    decision: DecisionType,
    reason: str,
    ctx: AutonomyContext,
    *,
    metadata: dict[str, Any] | None = None,
) -> AutonomyDecision:
    if decision in DISABLED_DECISIONS:
        decision = DecisionType.CONTINUE
        reason = f"{decision.value} is disabled in this branch. Falling back to CONTINUE."

    from uuid import uuid4

    return AutonomyDecision(
        decision=decision,
        reason=reason,
        risk_level=DECISION_RISK_MAP.get(decision, "unknown"),
        advisory=True,
        decision_id=str(uuid4()),
        context_snapshot=ctx.as_dict(),
        metadata=metadata or {},
    )


def _is_transient_error(error_type: str) -> bool:
    lowered = error_type.strip().lower()
    transient_keywords = (
        "timeout", "rate_limit", "quota", "throttl",
        "retryable", "transient", "overloaded",
        "service_unavailable", "503", "429",
        "connection_reset", "temporary",
    )
    return any(kw in lowered for kw in transient_keywords)

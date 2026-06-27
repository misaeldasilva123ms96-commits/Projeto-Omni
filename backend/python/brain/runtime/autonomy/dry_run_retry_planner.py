"""Pure dry-run RETRY planner.

This module creates advisory metadata only. It does not execute retries,
provider calls, tools, commands, file writes, patches, CI repair, or Git/PR
automation.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from .autonomy_models import AutonomyContext, AutonomyDecision, DecisionType
from .dry_run_retry_models import DryRunRetryPlan, safe_retry_text, utc_now_iso

_LOW_MEDIUM_RISK = {"low", "medium"}
_HIGH_RISK = {"high", "critical"}
_RETRY_LIKE_HINTS = {"retry", "retry_like", "retry_recommended", "try_again"}
_GOVERNANCE_BLOCKERS = {"pause", "paused", "escalate", "escalate_to_misael", "abort", "abort_safe"}


class DryRunRetryPlanner:
    """Builds a safe advisory dry-run retry plan from safe metadata."""

    def __init__(self, *, max_retry_attempts: int = 1) -> None:
        self.max_retry_attempts = max(0, int(max_retry_attempts or 0))

    def plan(
        self,
        *,
        decision: AutonomyDecision | DecisionType | str | None = None,
        context: AutonomyContext | dict[str, Any] | None = None,
        tracker: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> DryRunRetryPlan:
        safe_context = _context_dict(context)
        safe_tracker = _tracker_dict(safe_context, tracker)
        source_decision = _source_decision(decision)
        hint = safe_retry_text(safe_tracker.get("recommended_decision_hint", ""), max_length=64).lower()
        risk_level = _risk_level(decision)
        current_attempts = _current_retry_attempts(safe_context, safe_tracker)
        remaining = max(0, self.max_retry_attempts - current_attempts)
        retry_like = source_decision == DecisionType.RETRY.value or hint in _RETRY_LIKE_HINTS

        block_reasons = self._block_reasons(
            risk_level=risk_level,
            context=safe_context,
            remaining_attempts=remaining,
        )
        eligible = retry_like and risk_level in _LOW_MEDIUM_RISK and not block_reasons
        evidence_summary = safe_retry_text(safe_tracker.get("evidence_summary", ""))
        created = safe_retry_text(created_at or utc_now_iso(), max_length=64)

        return DryRunRetryPlan(
            plan_id=_plan_id(source_decision, safe_tracker, created),
            would_retry=eligible,
            retry_reason=_retry_reason(eligible=eligible, retry_like=retry_like, block_reasons=block_reasons),
            blocked=bool(block_reasons),
            block_reasons=block_reasons,
            retry_eligibility_score=_eligibility_score(retry_like=retry_like, risk_level=risk_level, block_reasons=block_reasons),
            risk_level=risk_level,
            source_decision=source_decision,
            fingerprint_id=safe_tracker.get("fingerprint_id", ""),
            stagnation_score=_safe_int(safe_tracker.get("stagnation_score")),
            progress_score=_safe_int(safe_tracker.get("progress_score")),
            repeated_strategy_count=_safe_int(safe_tracker.get("repeated_strategy_count")),
            max_attempts_remaining=remaining,
            evidence_summary=evidence_summary,
            created_at=created,
        )

    def _block_reasons(
        self,
        *,
        risk_level: str,
        context: dict[str, Any],
        remaining_attempts: int,
    ) -> list[str]:
        reasons: list[str] = []
        if risk_level in _HIGH_RISK:
            reasons.append("risk_too_high")
        if _safe_bool(context.get("secret_detected")):
            reasons.append("secret_detected")
        if _safe_bool(context.get("protected_file_involved")):
            reasons.append("protected_file_involved")
        if _safe_bool(context.get("provider_switching_required")):
            reasons.append("provider_switching_required")
        if _safe_bool(context.get("destructive_operation_required")) or _safe_bool(context.get("production_action_required")):
            reasons.append("destructive_operation_required")
        if _safe_bool(context.get("tool_action_required")):
            reasons.append("tool_action_required")
        if _safe_bool(context.get("write_action_required")):
            reasons.append("write_action_required")
        if _safe_bool(context.get("command_action_required")):
            reasons.append("command_action_required")
        if _safe_bool(context.get("unsafe_ci_signal")) or _safe_bool(context.get("security_signal")):
            reasons.append("unsafe_ci_or_security_signal")
        if _safe_bool(context.get("no_safe_next_action")):
            reasons.append("no_safe_next_action")
        if remaining_attempts <= 0:
            reasons.append("max_attempts_exceeded")
        governance = safe_retry_text(context.get("governance_decision", ""), max_length=64).lower()
        if governance in _GOVERNANCE_BLOCKERS:
            reasons.append(f"governance_{governance}")
        if _safe_bool(context.get("user_approval_required")):
            reasons.append("user_approval_required")
        return reasons


def build_dry_run_retry_plan(
    *,
    decision: AutonomyDecision | DecisionType | str | None = None,
    context: AutonomyContext | dict[str, Any] | None = None,
    tracker: dict[str, Any] | None = None,
    max_retry_attempts: int = 1,
    created_at: str | None = None,
) -> DryRunRetryPlan:
    return DryRunRetryPlanner(max_retry_attempts=max_retry_attempts).plan(
        decision=decision,
        context=context,
        tracker=tracker,
        created_at=created_at,
    )


def _context_dict(context: AutonomyContext | dict[str, Any] | None) -> dict[str, Any]:
    if context is None:
        return {}
    if isinstance(context, AutonomyContext):
        data = context.as_dict()
    elif isinstance(context, dict):
        data = dict(context)
    else:
        return {}
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            data.setdefault(key, value)
    return data


def _tracker_dict(context: dict[str, Any], tracker: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(tracker, dict):
        return dict(tracker)
    candidate = context.get("error_progress_tracker")
    if isinstance(candidate, dict):
        return dict(candidate)
    return {}


def _source_decision(decision: AutonomyDecision | DecisionType | str | None) -> str:
    if isinstance(decision, AutonomyDecision):
        return decision.decision.value
    if isinstance(decision, DecisionType):
        return decision.value
    raw = safe_retry_text(decision, max_length=48).upper()
    return raw


def _risk_level(decision: AutonomyDecision | DecisionType | str | None) -> str:
    if isinstance(decision, AutonomyDecision):
        risk = safe_retry_text(decision.risk_level, max_length=24).lower()
        return risk or "low"
    return "low"


def _current_retry_attempts(context: dict[str, Any], tracker: dict[str, Any]) -> int:
    for source in (context, tracker):
        for key in ("current_retry_attempts", "retry_attempts", "retry_count"):
            if key in source:
                return _safe_int(source.get(key))
    return 0


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _retry_reason(*, eligible: bool, retry_like: bool, block_reasons: list[str]) -> str:
    if eligible:
        return "retry_eligible"
    if block_reasons:
        return "retry_blocked"
    if not retry_like:
        return "not_retry_decision"
    return "retry_not_eligible"


def _eligibility_score(*, retry_like: bool, risk_level: str, block_reasons: list[str]) -> float:
    if not retry_like:
        return 0.0
    if block_reasons:
        return 0.0
    if risk_level == "low":
        return 1.0
    if risk_level == "medium":
        return 0.75
    return 0.0


def _plan_id(source_decision: str, tracker: dict[str, Any], created_at: str) -> str:
    fingerprint = safe_retry_text(tracker.get("fingerprint_id", ""), max_length=64)
    basis = "|".join([
        "dry_run_retry",
        source_decision,
        fingerprint,
        created_at,
    ])
    return "dry-retry-" + sha256(basis.encode("utf-8")).hexdigest()[:16]

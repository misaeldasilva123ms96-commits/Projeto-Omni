"""Pure dry-run REPLAN planner.

This module creates advisory metadata only. It does not rewrite prompts,
execute replans, call providers, execute tools or commands, write files,
patch code, repair CI, or automate Git/PR work.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from .autonomy_models import AutonomyContext, AutonomyDecision, DecisionType
from .dry_run_replan_models import DryRunReplanPlan, safe_replan_text, utc_now_iso

_LOW_MEDIUM_RISK = {"low", "medium"}
_HIGH_RISK = {"high", "critical"}
_REPLAN_LIKE_HINTS = {"replan", "replan_like", "replan_recommended", "change_strategy"}
_GOVERNANCE_BLOCKERS = {"pause", "paused", "escalate", "escalate_to_misael", "abort", "abort_safe"}
_STUCK_STRATEGY_THRESHOLD = 2


class DryRunReplanPlanner:
    """Builds a safe advisory dry-run replan plan from safe metadata."""

    def plan(
        self,
        *,
        decision: AutonomyDecision | DecisionType | str | None = None,
        context: AutonomyContext | dict[str, Any] | None = None,
        tracker: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> DryRunReplanPlan:
        safe_context = _context_dict(context)
        safe_tracker = _tracker_dict(safe_context, tracker)
        source_decision = _source_decision(decision)
        hint = safe_replan_text(safe_tracker.get("recommended_decision_hint", ""), max_length=64).lower()
        risk_level = _risk_level(decision)
        stagnation_score = _safe_int(safe_tracker.get("stagnation_score"))
        progress_score = _safe_int(safe_tracker.get("progress_score"))
        repeated_strategy_count = _safe_int(safe_tracker.get("repeated_strategy_count"))
        replan_like = source_decision == DecisionType.REPLAN.value or hint in _REPLAN_LIKE_HINTS
        repeated_retry_not_useful = _repeated_retry_not_useful(safe_context, safe_tracker)
        strategy_stuck = repeated_strategy_count >= _STUCK_STRATEGY_THRESHOLD
        stagnation_dominates = stagnation_score > progress_score

        block_reasons = self._block_reasons(
            risk_level=risk_level,
            context=safe_context,
            retry_still_useful=not repeated_retry_not_useful,
            stagnation_dominates=stagnation_dominates,
            strategy_stuck=strategy_stuck,
            replan_like=replan_like,
        )
        eligible = (
            replan_like
            and repeated_retry_not_useful
            and stagnation_dominates
            and strategy_stuck
            and risk_level in _LOW_MEDIUM_RISK
            and not block_reasons
        )
        evidence_summary = safe_replan_text(safe_tracker.get("evidence_summary", ""))
        created = safe_replan_text(created_at or utc_now_iso(), max_length=64)

        return DryRunReplanPlan(
            plan_id=_plan_id(source_decision, safe_tracker, created),
            would_replan=eligible,
            replan_reason=_replan_reason(
                eligible=eligible,
                replan_like=replan_like,
                block_reasons=block_reasons,
            ),
            blocked=bool(block_reasons),
            block_reasons=block_reasons,
            replan_eligibility_score=_eligibility_score(
                replan_like=replan_like,
                repeated_retry_not_useful=repeated_retry_not_useful,
                stagnation_dominates=stagnation_dominates,
                strategy_stuck=strategy_stuck,
                risk_level=risk_level,
                block_reasons=block_reasons,
            ),
            risk_level=risk_level,
            source_decision=source_decision,
            fingerprint_id=safe_tracker.get("fingerprint_id", ""),
            stagnation_score=stagnation_score,
            progress_score=progress_score,
            repeated_strategy_count=repeated_strategy_count,
            suggested_strategy=_suggested_strategy(safe_context, safe_tracker, eligible=eligible, replan_like=replan_like),
            evidence_summary=evidence_summary,
            created_at=created,
        )

    def _block_reasons(
        self,
        *,
        risk_level: str,
        context: dict[str, Any],
        retry_still_useful: bool,
        stagnation_dominates: bool,
        strategy_stuck: bool,
        replan_like: bool,
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
        governance = safe_replan_text(context.get("governance_decision", ""), max_length=64).lower()
        if governance in _GOVERNANCE_BLOCKERS:
            reasons.append(f"governance_{governance}")
        if _safe_bool(context.get("user_approval_required")):
            reasons.append("user_approval_required")
        if _safe_bool(context.get("prompt_rewrite_required")) or _safe_bool(context.get("replan_requires_prompt_rewrite")):
            reasons.append("prompt_rewrite_required")
        if _safe_bool(context.get("model_call_required")) or _safe_bool(context.get("provider_call_required")):
            reasons.append("model_or_provider_call_required")
        if replan_like and retry_still_useful:
            reasons.append("retry_still_useful")
        if replan_like and not stagnation_dominates:
            reasons.append("stagnation_not_dominant")
        if replan_like and not strategy_stuck:
            reasons.append("strategy_not_stuck")
        return reasons


def build_dry_run_replan_plan(
    *,
    decision: AutonomyDecision | DecisionType | str | None = None,
    context: AutonomyContext | dict[str, Any] | None = None,
    tracker: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> DryRunReplanPlan:
    return DryRunReplanPlanner().plan(
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
    raw = safe_replan_text(decision, max_length=48).upper()
    return raw


def _risk_level(decision: AutonomyDecision | DecisionType | str | None) -> str:
    if isinstance(decision, AutonomyDecision):
        risk = safe_replan_text(decision.risk_level, max_length=24).lower()
        return risk or "low"
    return "low"


def _repeated_retry_not_useful(context: dict[str, Any], tracker: dict[str, Any]) -> bool:
    if _safe_bool(context.get("repeated_retry_not_useful")):
        return True
    if "retry_still_useful" in context:
        return not _safe_bool(context.get("retry_still_useful"))
    retry_plan = context.get("dry_run_retry_plan")
    if isinstance(retry_plan, dict):
        if retry_plan.get("would_retry") is False:
            return True
        block_reasons = retry_plan.get("block_reasons")
        if isinstance(block_reasons, list) and "max_attempts_exceeded" in block_reasons:
            return True
    if _safe_bool(tracker.get("repeated_retry_not_useful")):
        return True
    return False


def _suggested_strategy(
    context: dict[str, Any],
    tracker: dict[str, Any],
    *,
    eligible: bool,
    replan_like: bool,
) -> str:
    candidate = context.get("suggested_strategy") or tracker.get("suggested_strategy")
    if candidate:
        return safe_replan_text(candidate, max_length=64)
    if eligible or replan_like:
        return "change_safe_strategy_category"
    return ""


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


def _replan_reason(*, eligible: bool, replan_like: bool, block_reasons: list[str]) -> str:
    if eligible:
        return "replan_eligible"
    if block_reasons:
        return "replan_blocked"
    if not replan_like:
        return "not_replan_decision"
    return "replan_not_eligible"


def _eligibility_score(
    *,
    replan_like: bool,
    repeated_retry_not_useful: bool,
    stagnation_dominates: bool,
    strategy_stuck: bool,
    risk_level: str,
    block_reasons: list[str],
) -> float:
    if not replan_like or block_reasons:
        return 0.0
    score = 0.0
    if repeated_retry_not_useful:
        score += 0.25
    if stagnation_dominates:
        score += 0.25
    if strategy_stuck:
        score += 0.25
    if risk_level == "low":
        score += 0.25
    elif risk_level == "medium":
        score += 0.15
    return min(1.0, round(score, 3))


def _plan_id(source_decision: str, tracker: dict[str, Any], created_at: str) -> str:
    fingerprint = safe_replan_text(tracker.get("fingerprint_id", ""), max_length=64)
    basis = "|".join([
        "dry_run_replan",
        source_decision,
        fingerprint,
        created_at,
    ])
    return "dry-replan-" + sha256(basis.encode("utf-8")).hexdigest()[:16]

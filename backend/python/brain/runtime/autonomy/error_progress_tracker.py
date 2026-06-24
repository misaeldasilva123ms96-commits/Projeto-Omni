"""Smart Error Progress Tracker for advisory autonomy decisions.

Classifies repeated errors, progress, stagnation and strategy attempts
using safe metadata only. Produces structured evidence for the Autonomy
Controller. No autonomous execution.
"""

from __future__ import annotations

import logging
from typing import Any

from .autonomy_models import AutonomyContext, AutonomyDecision, DecisionType
from .error_progress_models import (
    ErrorFingerprint,
    ProgressTrackerOutput,
    StrategyAttempt,
)

logger = logging.getLogger(__name__)

_RUNTIME_MODE_ORDER: dict[str, int] = {
    "provider_failure": 0,
    "safe_fallback": 1,
    "node_fallback": 2,
    "standard": 3,
    "default": 3,
    "normal": 3,
}

_SAFE_FALLBACK_TEXT = "Nao consegui processar isso ainda, mas estou aprendendo."


def _classify_failure_reason(reason: str) -> str:
    lowered = reason.strip().lower()
    if not lowered:
        return ""
    if any(kw in lowered for kw in ("timeout", "timed out")):
        return "timeout"
    if any(kw in lowered for kw in ("rate_limit", "quota", "throttl")):
        return "rate_limit"
    if any(kw in lowered for kw in ("auth", "unauthorized", "forbidden", "permission")):
        return "auth"
    if any(kw in lowered for kw in ("provider", "api_error")):
        return "provider"
    if any(kw in lowered for kw in ("node", "runtime")):
        return "runtime"
    if any(kw in lowered for kw in ("parse", "syntax", "invalid")):
        return "parse"
    return "other"


def _map_decision_to_strategy(decision: AutonomyDecision, ctx: AutonomyContext) -> str:
    dt = decision.decision
    if dt == DecisionType.CONTINUE:
        return "no_op"
    if dt == DecisionType.RETRY:
        if ctx.metadata.get("provider_failure_type", ""):
            return "provider_retry"
        return "retry_same"
    if dt == DecisionType.REPLAN:
        return "replan"
    if dt == DecisionType.ABORT_SAFE:
        return "safe_abort"
    if dt == DecisionType.ESCALATE_TO_MISAEL:
        return "escalate"
    if dt == DecisionType.PAUSE:
        return "pause"
    return "no_op"


class SmartErrorProgressTracker:
    """Tracks error fingerprints, progress/stagnation scoring, and strategies.

    Process-local. All data derived from safe metadata only.
    No raw prompts, responses, or secrets stored.
    """

    def __init__(self) -> None:
        self._fingerprints: dict[str, list[ErrorFingerprint]] = {}
        self._strategies: dict[str, list[StrategyAttempt]] = {}

    def build_fingerprint(
        self,
        ctx: AutonomyContext,
        inspection: dict[str, Any] | None,
    ) -> ErrorFingerprint:
        failure_class = ""
        failure_reason_raw = ""
        tool_category = ""

        if isinstance(inspection, dict):
            signals: dict[str, Any] = inspection.get("signals") or {}
            failure_class = str(signals.get("failure_class") or "")
            failure_reason_raw = str(signals.get("failure_reason") or "")
            tool_category = str(signals.get("tool_category") or signals.get("tool") or "")

        failure_reason_category = _classify_failure_reason(failure_reason_raw)

        runtime_mode: str = ctx.metadata.get("runtime_mode", "")
        provider_failure_type: str = ctx.metadata.get("provider_failure_type", "")
        governance_decision: str = ctx.metadata.get("last_decision", "")

        return ErrorFingerprint(
            error_type=ctx.error_type,
            failure_class=failure_class,
            failure_reason_category=failure_reason_category,
            runtime_mode=runtime_mode,
            provider_failure_type=provider_failure_type,
            tool_category=tool_category,
            governance_decision=governance_decision,
            protected_file_flag=ctx.protected_file_involved,
            secret_detected_flag=ctx.secret_detected,
        )

    def _last_fingerprint(self, session_id: str) -> ErrorFingerprint | None:
        history = self._fingerprints.get(session_id, [])
        if history:
            return history[-1]
        return None

    def _count_stagnation_signals(
        self,
        current: ErrorFingerprint,
        previous: ErrorFingerprint | None,
        ctx: AutonomyContext,
        strategies: list[StrategyAttempt],
    ) -> int:
        score = 0

        if previous is None:
            return 0

        if not current.is_empty() and not previous.is_empty():
            if current.fingerprint_id == previous.fingerprint_id:
                score += 1

        if current.failure_class and previous.failure_class:
            if current.failure_class == previous.failure_class:
                score += 1

        if current.provider_failure_type and previous.provider_failure_type:
            if current.provider_failure_type == previous.provider_failure_type:
                score += 1

        if current.runtime_mode in ("safe_fallback", "provider_failure", "node_fallback"):
            if current.runtime_mode == previous.runtime_mode:
                score += 1

        if ctx.no_safe_next_action:
            if previous.runtime_mode in ("safe_fallback",):
                score += 1

        if current.governance_decision and previous.governance_decision:
            if current.governance_decision == previous.governance_decision:
                score += 1

        if strategies:
            last_strategy = strategies[-1].strategy_name
            last_two = [s.strategy_name for s in strategies[-2:]]
            if len(last_two) == 2 and last_two[0] == last_two[1]:
                score += 1

        return score

    def _count_progress_signals(
        self,
        current: ErrorFingerprint,
        previous: ErrorFingerprint | None,
        ctx: AutonomyContext,
    ) -> int:
        score = 0

        if previous is None:
            return 0

        if current.error_type and previous.error_type:
            if current.fingerprint_id != previous.fingerprint_id:
                score += 1

        if current.failure_class and previous.failure_class:
            if current.failure_class != previous.failure_class:
                score += 1

        current_rank = _RUNTIME_MODE_ORDER.get(current.runtime_mode, -1)
        last_rank = _RUNTIME_MODE_ORDER.get(previous.runtime_mode, -1)
        if current_rank > last_rank:
            score += 1

        if previous.provider_failure_type and not current.provider_failure_type:
            score += 1

        if previous.runtime_mode in ("safe_fallback", "node_fallback", "provider_failure"):
            if current.runtime_mode not in ("safe_fallback", "node_fallback", "provider_failure"):
                score += 1

        prev_response_len: int = 0
        current_response_len: Any = ctx.metadata.get("response_length", 0)
        if isinstance(current_response_len, str):
            try:
                current_response_len = int(current_response_len)
            except (ValueError, TypeError):
                current_response_len = 0
        if prev_response_len == 0 and current_response_len > 0:
            score += 1

        if ctx.no_safe_next_action is False:
            prev_safe = previous.runtime_mode in ("safe_fallback",) or str(previous.runtime_mode) == "safe_fallback"
            if prev_safe:
                score += 1

        return score

    def _build_evidence(
        self,
        fp: ErrorFingerprint,
        output: ProgressTrackerOutput,
    ) -> str:
        parts: list[str] = []
        parts.append(f"fingerprint={fp.fingerprint_id}")
        if output.is_new_error:
            parts.append("new_error")
        if output.is_repeated_error:
            parts.append("repeated_error")
        if output.is_progress:
            parts.append("progress")
        if output.is_stagnation:
            parts.append("stagnation")
        parts.append(f"progress_score={output.progress_score}")
        parts.append(f"stagnation_score={output.stagnation_score}")
        parts.append(f"stagnant_attempts={output.stagnant_attempts}")
        parts.append(f"distinct_errors={output.distinct_error_count}")
        if output.strategies_attempted:
            parts.append(f"strategies={','.join(output.strategies_attempted[-3:])}")
        if output.recommended_decision_hint:
            parts.append(f"hint={output.recommended_decision_hint}")
        return " | ".join(parts)

    def classify(
        self,
        session_id: str,
        ctx: AutonomyContext,
        inspection: dict[str, Any] | None,
    ) -> ProgressTrackerOutput:
        current_fp = self.build_fingerprint(ctx, inspection)
        previous_fp = self._last_fingerprint(session_id)
        strategies = self._strategies.get(session_id, [])

        is_new = previous_fp is None
        is_repeated = False
        if previous_fp is not None:
            if not current_fp.is_empty() and not previous_fp.is_empty():
                is_repeated = current_fp.fingerprint_id == previous_fp.fingerprint_id
            is_new = not is_repeated and not is_new

        stagnation_score = self._count_stagnation_signals(current_fp, previous_fp, ctx, strategies)
        progress_score = self._count_progress_signals(current_fp, previous_fp, ctx)

        distinct = len({f.fingerprint_id for f in self._fingerprints.get(session_id, [])})
        if not current_fp.is_empty():
            all_ids = {f.fingerprint_id for f in self._fingerprints.get(session_id, [])}
            all_ids.add(current_fp.fingerprint_id)
            distinct = len(all_ids)

        if current_fp.is_empty():
            distinct = len({f.fingerprint_id for f in self._fingerprints.get(session_id, [])})

        strategy_names = [s.strategy_name for s in strategies]
        repeated_strat = 0
        if len(strategy_names) >= 2:
            if strategy_names[-1] == strategy_names[-2]:
                repeated_strat = sum(
                    1 for i in range(1, len(strategy_names))
                    if strategy_names[i] == strategy_names[i - 1]
                )

        stagnant_count = 0
        for i in range(1, len(self._fingerprints.get(session_id, []))):
            if self._fingerprints[session_id][i].fingerprint_id == self._fingerprints[session_id][i - 1].fingerprint_id:
                stagnant_count += 1

        hint = ""
        if stagnation_score > progress_score and stagnation_score >= 3:
            hint = "ESCALATE_TO_MISAEL"
        elif stagnation_score > progress_score:
            hint = "RETRY"
        elif progress_score > stagnation_score:
            hint = "CONTINUE"
        else:
            hint = "CONTINUE"

        if ctx.no_safe_next_action:
            hint = "ABORT_SAFE"

        if current_fp.protected_file_flag or current_fp.secret_detected_flag:
            hint = "ESCALATE_TO_MISAEL"

        output = ProgressTrackerOutput(
            fingerprint_id=current_fp.fingerprint_id,
            is_new_error=is_new,
            is_repeated_error=is_repeated,
            progress_score=progress_score,
            stagnation_score=stagnation_score,
            stagnant_attempts=stagnant_count,
            distinct_error_count=distinct,
            strategies_attempted=strategy_names,
            repeated_strategy_count=repeated_strat,
            recommended_decision_hint=hint,
            evidence_summary="",
        )

        output.evidence_summary = self._build_evidence(current_fp, output)
        return output

    def record_strategy(
        self,
        session_id: str,
        strategy_name: str,
        ctx: AutonomyContext,
    ) -> None:
        if session_id not in self._strategies:
            self._strategies[session_id] = []
        fp = self._last_fingerprint(session_id)
        attempt = StrategyAttempt(
            strategy_name=strategy_name,
            fingerprint_id=fp.fingerprint_id if fp else "",
        )
        self._strategies[session_id].append(attempt)

    def update(
        self,
        session_id: str,
        ctx: AutonomyContext,
        inspection: dict[str, Any] | None,
        decision: AutonomyDecision,
    ) -> ProgressTrackerOutput:
        output = self.classify(session_id, ctx, inspection)
        current_fp = self.build_fingerprint(ctx, inspection)

        if session_id not in self._fingerprints:
            self._fingerprints[session_id] = []
        self._fingerprints[session_id].append(current_fp)

        strategy_name = _map_decision_to_strategy(decision, ctx)
        self.record_strategy(session_id, strategy_name, ctx)

        return output

    def reset(self, session_id: str) -> None:
        self._fingerprints.pop(session_id, None)
        self._strategies.pop(session_id, None)

    def reset_all(self) -> None:
        self._fingerprints.clear()
        self._strategies.clear()

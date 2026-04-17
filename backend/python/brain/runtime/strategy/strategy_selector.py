from __future__ import annotations

from brain.runtime.language.oil_schema import OILRequest

from .strategy_models import ExecutionStrategy, StrategyDecision
from .strategy_rules import apply_learning_adjustments, baseline_strategy, conservative_fallback_strategy
from .strategy_trace import StrategyAdaptationTrace


class StrategySelector:
    """Rule-driven strategy selection (Phase 35) — no hidden mutation."""

    def select(
        self,
        *,
        session_id: str | None,
        run_id: str | None,
        message: str,
        oil_request: OILRequest,
        memory_context: dict[str, Any],
        learning_record: dict[str, Any] | None,
    ) -> StrategyDecision:
        base = baseline_strategy(message=message, oil_request=oil_request, memory_context=memory_context)
        adjusted, tags, reason = apply_learning_adjustments(base, learning_record=learning_record)
        fallback = conservative_fallback_strategy()

        learning_id = str(learning_record.get("record_id", "")).strip() if learning_record else None
        assessment = learning_record.get("assessment") if isinstance(learning_record, dict) else None
        loclass = None
        if isinstance(assessment, dict):
            loclass = str(assessment.get("outcome_class", "") or "").strip() or None

        confidence = 0.58
        if learning_record:
            confidence += 0.12
        if memory_context.get("selected_count", 0):
            confidence += 0.08
        if oil_request.extensions.get("confidence") is not None:
            confidence += 0.05
        confidence = max(0.35, min(0.95, confidence))

        trace = StrategyAdaptationTrace.build(
            session_id=session_id,
            run_id=run_id,
            selected_mode=adjusted.mode,
            selected_path=adjusted.path,
            validation_level=adjusted.validation_level,
            reasoning_depth=adjusted.reasoning_depth,
            risk_tolerance=adjusted.risk_tolerance,
            fallback_mode=fallback.mode,
            fallback_path=fallback.path,
            signals_used=tags,
            learning_record_id=learning_id,
            learning_outcome_class=loclass,
        )

        return StrategyDecision(
            selected_strategy=adjusted,
            fallback_strategy=fallback,
            reason=reason,
            confidence=confidence,
            signals_used=tags,
            trace=trace,
            metadata={
                "baseline_mode": base.mode,
                "baseline_path": base.path,
            },
        )

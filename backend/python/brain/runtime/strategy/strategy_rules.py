from __future__ import annotations

from typing import Any

from brain.runtime.language.oil_schema import OILRequest

from .strategy_models import ExecutionStrategy


_CRITICAL_TOKENS = (
    "production",
    "credential",
    "secret",
    "drop ",
    "delete ",
    "rm -rf",
    "security",
)


def conservative_fallback_strategy() -> ExecutionStrategy:
    """Safe default if primary selection is unavailable — does not bypass governance."""
    return ExecutionStrategy(
        mode="fast",
        path="swarm",
        validation_level="medium",
        reasoning_depth=2,
        risk_tolerance=0.65,
    )


def baseline_strategy(*, message: str, oil_request: OILRequest, memory_context: dict[str, Any]) -> ExecutionStrategy:
    text = (message or "").lower()
    if any(tok in text for tok in _CRITICAL_TOKENS):
        return ExecutionStrategy(
            mode="critical",
            path="guarded",
            validation_level="high",
            reasoning_depth=5,
            risk_tolerance=0.25,
        )

    intent = str(oil_request.intent or "").strip()
    conf = float(oil_request.extensions.get("confidence", 0) or 0.0)
    mem = int(memory_context.get("selected_count", 0) or 0)
    boost = min(0.12, mem * 0.015)

    if intent in {"analyze", "plan", "execute_tool_like_action"} or len(message) > 160:
        return ExecutionStrategy(
            mode="deep",
            path="swarm",
            validation_level="medium",
            reasoning_depth=4,
            risk_tolerance=min(0.78, 0.52 + boost),
        )
    if intent in {"ask_question", "summarize"} and conf > 0.45:
        return ExecutionStrategy(
            mode="fast",
            path="direct",
            validation_level="low",
            reasoning_depth=2,
            risk_tolerance=min(0.92, 0.86 + boost),
        )
    return ExecutionStrategy(
        mode="fast",
        path="swarm",
        validation_level="low",
        reasoning_depth=2,
        risk_tolerance=min(0.85, 0.72 + boost),
    )


def _learning_negative_count(record: dict[str, Any] | None) -> int:
    if not record or not isinstance(record.get("signals"), list):
        return 0
    return sum(1 for s in record["signals"] if isinstance(s, dict) and str(s.get("polarity", "")).strip() == "negative")


def apply_learning_adjustments(
    base: ExecutionStrategy,
    *,
    learning_record: dict[str, Any] | None,
) -> tuple[ExecutionStrategy, list[str], str]:
    """Return adjusted strategy and human-readable signal tags (bounded heuristics)."""
    tags: list[str] = []
    if not learning_record:
        tags.append("learning:absent")
        return base, tags, "No prior runtime learning record; using OIL+memory baseline."

    assessment = learning_record.get("assessment") if isinstance(learning_record.get("assessment"), dict) else {}
    oclass = str(assessment.get("outcome_class", "") or "").lower()
    duration_ms = int(assessment.get("duration_ms", 0) or 0)
    neg = _learning_negative_count(learning_record)

    tags.append(f"learning_outcome:{oclass or 'unknown'}")
    tags.append(f"learning_negative_signals:{neg}")
    tags.append(f"learning_duration_ms:{duration_ms}")

    s = ExecutionStrategy(
        mode=base.mode,
        path=base.path,
        validation_level=base.validation_level,
        reasoning_depth=base.reasoning_depth,
        risk_tolerance=base.risk_tolerance,
    )
    reason_parts: list[str] = ["Baseline strategy adjusted with Phase 34 learning hints."]

    if oclass == "failure" or neg >= 2:
        if s.mode == "fast":
            s = ExecutionStrategy("deep", "guarded", "high", 4, min(s.risk_tolerance, 0.38))
        elif s.mode == "deep":
            s = ExecutionStrategy("deep", "guarded", "high", max(s.reasoning_depth, 4), min(s.risk_tolerance, 0.42))
        else:
            s = ExecutionStrategy("critical", "guarded", "high", max(s.reasoning_depth, 5), min(s.risk_tolerance, 0.32))
        reason_parts.append("Recent failures or multiple negative learning signals → deeper, guarded path.")
    elif oclass == "degraded" and neg >= 1:
        s = ExecutionStrategy(
            mode="deep" if s.mode == "fast" else s.mode,
            path="guarded" if s.path != "guarded" else s.path,
            validation_level="high" if s.validation_level == "low" else s.validation_level,
            reasoning_depth=max(s.reasoning_depth, 3),
            risk_tolerance=min(s.risk_tolerance, 0.55),
        )
        reason_parts.append("Degraded prior outcome → increased validation and guarded execution path.")

    if duration_ms > 45_000 and s.mode == "deep" and oclass == "success":
        s = ExecutionStrategy(
            mode="fast",
            path="swarm",
            validation_level="medium",
            reasoning_depth=2,
            risk_tolerance=min(0.82, s.risk_tolerance + 0.08),
        )
        reason_parts.append("Prior successful but slow turn → bias away from deep mode to reduce latency risk.")

    return s, tags, " ".join(reason_parts)

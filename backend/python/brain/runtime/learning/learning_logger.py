from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .learning_improvement_engine import LearningImprovementEngine
from .learning_models import (
    DecisionEvaluation,
    ExecutionOutcome,
    LearningRecord,
    new_controlled_learning_record_id,
)
from .learning_store import ControlledLearningStore
from .models import utc_now_iso


_SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-\.=]{12,}", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    (re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE), "[REDACTED_EMAIL]"),
]


class LearningLogger:
    """Phase 10 controlled learning logger. Records outcomes, evaluates decisions, and emits advisory signals."""

    def __init__(self, root: Path) -> None:
        self.store = ControlledLearningStore(root)
        self.improvement_engine = LearningImprovementEngine()

    def log_turn(
        self,
        *,
        input_text: str,
        response_text: str,
        strategy_execution: dict[str, Any] | None,
        decision_ranking: dict[str, Any] | None,
        cognitive_runtime_inspection: dict[str, Any] | None,
        tool_execution: dict[str, Any] | None,
    ) -> dict[str, Any]:
        inspection = dict(cognitive_runtime_inspection or {})
        signals = dict(inspection.get("signals") or {})
        strategy_execution = dict(strategy_execution or {})
        decision_ranking = dict(decision_ranking or {})
        tool_execution = dict(tool_execution or signals.get("tool_execution") or {})

        selected_strategy = str(
            strategy_execution.get("selected_strategy")
            or decision_ranking.get("selected_strategy")
            or signals.get("ranked_strategy")
            or signals.get("deterministic_strategy")
            or ""
        ).strip()
        selected_tool = str(
            tool_execution.get("tool_selected")
            or (signals.get("decision_suggested_tools") or [""])[0]
            or ""
        ).strip()
        execution_path = str(signals.get("execution_path_used", "") or "").strip()
        runtime_mode = str(inspection.get("runtime_mode", "") or "").strip()
        failure_class = str(signals.get("failure_class", "") or "").strip()
        provider_actual = str(signals.get("provider_actual", "") or "").strip()
        fallback_triggered = bool(signals.get("fallback_triggered", False))
        compatibility_execution_active = bool(signals.get("compatibility_execution_active", False))
        provider_failed = bool(signals.get("provider_failed", False))
        tool_succeeded = _coerce_bool(tool_execution.get("tool_succeeded"))
        tool_failed = _coerce_bool(tool_execution.get("tool_failed"))
        tool_denied = _coerce_bool(tool_execution.get("tool_denied"))

        outcome = ExecutionOutcome(
            execution_path=execution_path,
            runtime_mode=runtime_mode,
            success=self._execution_success(runtime_mode, failure_class, fallback_triggered, provider_failed, tool_succeeded, tool_failed),
            fallback_triggered=fallback_triggered,
            compatibility_execution_active=compatibility_execution_active,
            failure_class=failure_class,
            provider_actual=provider_actual,
            provider_failed=provider_failed,
            tool_used=selected_tool,
            tool_succeeded=tool_succeeded,
            tool_failed=tool_failed,
            tool_denied=tool_denied,
        )
        decision_eval = self._evaluate_decision(
            selected_strategy=selected_strategy,
            selected_tool=selected_tool,
            execution_path=execution_path,
            fallback_triggered=fallback_triggered,
            compatibility_execution_active=compatibility_execution_active,
            runtime_mode=runtime_mode,
            signals=signals,
            outcome=outcome,
        )
        record = LearningRecord(
            record_id=new_controlled_learning_record_id(),
            timestamp=utc_now_iso(),
            input_preview=self._sanitize_text(input_text),
            input_hash=self._hash_text(input_text),
            selected_strategy=selected_strategy,
            selected_tool=selected_tool,
            execution_path=execution_path,
            runtime_mode=runtime_mode,
            success=outcome.success,
            failure_class=failure_class,
            decision_evaluation=decision_eval,
            execution_outcome=outcome,
            provider_actual=provider_actual,
            notes=self._sanitize_text(response_text, limit=160),
            metadata={
                "decision_reasoning": self._sanitize_text(str(signals.get("decision_reasoning", "") or ""), limit=220),
                "decision_reason_codes": list(signals.get("decision_reason_codes", []) or []),
                "decision_must_execute": bool(signals.get("decision_must_execute", False)),
                "decision_requires_tools": bool(signals.get("decision_requires_tools", False)),
                "decision_requires_node_runtime": bool(signals.get("decision_requires_node_runtime", False)),
                "decision_suggested_tools": list(signals.get("decision_suggested_tools", []) or []),
                "node_execution_successful": bool(signals.get("node_execution_successful", False)),
                "tool_execution": dict(tool_execution) if tool_execution else None,
            },
        )
        stored = self.store.append_learning_record(record.as_dict())
        improvement_signals = self.improvement_engine.generate(record)
        stored_signal_count = 0
        for signal in improvement_signals:
            if self.store.append_improvement_signal(signal.as_dict()):
                stored_signal_count += 1
        return {
            "record": record.as_dict(),
            "learning_record_created": stored,
            "decision_correct": decision_eval.decision_correct,
            "decision_issue": decision_eval.decision_issue,
            "improvement_signals": [signal.as_dict() for signal in improvement_signals],
            "stored_signal_count": stored_signal_count,
            "storage_path": str(self.store.records_path),
            "signals_path": str(self.store.signals_path),
        }

    def _evaluate_decision(
        self,
        *,
        selected_strategy: str,
        selected_tool: str,
        execution_path: str,
        fallback_triggered: bool,
        compatibility_execution_active: bool,
        runtime_mode: str,
        signals: dict[str, Any],
        outcome: ExecutionOutcome,
    ) -> DecisionEvaluation:
        tool_required = bool(signals.get("decision_must_execute", False) or signals.get("decision_requires_tools", False))
        expected_tool = str((signals.get("decision_suggested_tools") or [""])[0] or "").strip()
        if tool_required and not selected_tool:
            return DecisionEvaluation(
                decision_correct=False,
                decision_issue="tool_required_but_not_used",
                notes="Decision required execution but no tool was selected.",
                expected_execution=True,
                expected_tool=expected_tool,
            )
        if tool_required and compatibility_execution_active:
            return DecisionEvaluation(
                decision_correct=False,
                decision_issue="compatibility_used_when_execution_required",
                notes="Compatibility execution remained active for a must_execute turn.",
                expected_execution=True,
                expected_tool=expected_tool,
            )
        if fallback_triggered and tool_required and not outcome.provider_failed and not outcome.tool_denied:
            return DecisionEvaluation(
                decision_correct=False,
                decision_issue="fallback_misuse",
                notes="Fallback triggered even though the decision expected a real execution path.",
                expected_execution=True,
                expected_tool=expected_tool,
            )
        if expected_tool and selected_tool and expected_tool != selected_tool:
            return DecisionEvaluation(
                decision_correct=False,
                decision_issue="wrong_tool",
                notes=f"Expected tool {expected_tool} but selected {selected_tool}.",
                expected_execution=tool_required,
                expected_tool=expected_tool,
            )
        if outcome.tool_failed:
            return DecisionEvaluation(
                decision_correct=False,
                decision_issue="tool_execution_failed",
                notes="The decision reached the tool runtime but the tool failed.",
                expected_execution=tool_required,
                expected_tool=expected_tool,
            )
        if outcome.success:
            return DecisionEvaluation(
                decision_correct=True,
                decision_issue="",
                notes=f"Decision completed successfully via {execution_path or runtime_mode}.",
                expected_execution=tool_required,
                expected_tool=expected_tool,
            )
        return DecisionEvaluation(
            decision_correct=None,
            decision_issue="needs_review",
            notes="Outcome was neither a clean success nor a rule-based decision failure.",
            expected_execution=tool_required,
            expected_tool=expected_tool,
        )

    @staticmethod
    def _execution_success(
        runtime_mode: str,
        failure_class: str,
        fallback_triggered: bool,
        provider_failed: bool,
        tool_succeeded: bool | None,
        tool_failed: bool | None,
    ) -> bool:
        if provider_failed or failure_class or fallback_triggered:
            return False
        if tool_failed is True:
            return False
        if tool_succeeded is True:
            return True
        return runtime_mode in {
            "FULL_COGNITIVE_RUNTIME",
            "NODE_EXECUTION_SUCCESS",
            "LOCAL_TOOL_SUCCESS",
            "MATCHER_SHORTCUT",
            "DIRECT_LOCAL_RESPONSE",
        }

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()

    def _sanitize_text(self, value: str, *, limit: int = 240) -> str:
        sanitized = str(value or "").strip()
        for pattern, replacement in _SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized[:limit]


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None

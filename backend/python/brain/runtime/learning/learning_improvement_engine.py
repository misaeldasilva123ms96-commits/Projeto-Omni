from __future__ import annotations

from typing import Any

from .learning_models import ImprovementSignal, LearningRecord, new_improvement_signal_id


class LearningImprovementEngine:
    """Generate bounded advisory signals from recorded decisions. No auto-apply behavior."""

    def generate(self, record: LearningRecord) -> list[ImprovementSignal]:
        signals: list[ImprovementSignal] = []
        issue = str(record.decision_evaluation.decision_issue or "").strip()
        metadata = dict(record.metadata or {})
        selected_tool = str(record.selected_tool or "").strip()
        input_preview = str(record.input_preview or "").lower()

        if issue == "tool_required_but_not_used" and "arquivo" in input_preview:
            signals.append(
                ImprovementSignal(
                    signal_id=new_improvement_signal_id(),
                    type="ROUTING_IMPROVEMENT",
                    pattern="file_analysis_without_tool",
                    suggestion="Prefer read_file for explicit file-analysis prompts before free-form synthesis.",
                    confidence=0.82,
                    evidence_summary={
                        "selected_strategy": record.selected_strategy,
                        "execution_path": record.execution_path,
                    },
                )
            )
        if issue == "fallback_misuse":
            signals.append(
                ImprovementSignal(
                    signal_id=new_improvement_signal_id(),
                    type="FALLBACK_REDUCTION",
                    pattern="fallback_used_when_execution_expected",
                    suggestion="Review routing rules so execution-required prompts do not degrade to fallback when a supported path exists.",
                    confidence=0.78,
                    evidence_summary={
                        "runtime_mode": record.runtime_mode,
                        "decision_must_execute": bool(metadata.get("decision_must_execute", False)),
                    },
                )
            )
        if issue == "compatibility_used_when_execution_required":
            signals.append(
                ImprovementSignal(
                    signal_id=new_improvement_signal_id(),
                    type="EXECUTION_PROMOTION",
                    pattern="compatibility_execution_for_required_action",
                    suggestion="Promote a real execution lane before compatibility execution for prompts marked as must_execute.",
                    confidence=0.8,
                    evidence_summary={
                        "execution_path": record.execution_path,
                        "selected_tool": selected_tool,
                    },
                )
            )
        if issue == "wrong_tool":
            signals.append(
                ImprovementSignal(
                    signal_id=new_improvement_signal_id(),
                    type="TOOL_SELECTION_IMPROVEMENT",
                    pattern="suboptimal_tool_selection",
                    suggestion="Tighten deterministic tool selection for this prompt family to avoid planner-selected but unsupported tools.",
                    confidence=0.73,
                    evidence_summary={"selected_tool": selected_tool},
                )
            )
        if record.execution_outcome.tool_failed:
            signals.append(
                ImprovementSignal(
                    signal_id=new_improvement_signal_id(),
                    type="TOOL_RUNTIME_IMPROVEMENT",
                    pattern="tool_execution_failure",
                    suggestion="Investigate the selected tool runtime and error handling before changing high-level routing.",
                    confidence=0.76,
                    evidence_summary={
                        "tool_used": selected_tool,
                        "failure_class": record.failure_class,
                    },
                )
            )
        if record.execution_outcome.provider_failed:
            signals.append(
                ImprovementSignal(
                    signal_id=new_improvement_signal_id(),
                    type="PROVIDER_DIAGNOSTIC_IMPROVEMENT",
                    pattern="provider_failure_during_execution",
                    suggestion="Improve provider routing or failure classification; this record reflects a provider-layer problem, not a decision-only issue.",
                    confidence=0.7,
                    evidence_summary={
                        "provider_actual": record.provider_actual,
                        "failure_class": record.failure_class,
                    },
                )
            )
        return signals

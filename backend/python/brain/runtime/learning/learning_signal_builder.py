from __future__ import annotations

from .models import LearningPolicy, LearningSignal, LearningSignalType, PatternRecord, StrategyRanking


class LearningSignalBuilder:
    def build(self, *, rankings: list[StrategyRanking], records: list[PatternRecord], policy: LearningPolicy) -> list[LearningSignal]:
        signals: list[LearningSignal] = []
        for ranking in rankings:
            weight = min(policy.max_signal_weight, max(0.05, ranking.score * policy.max_signal_weight))
            metadata = dict(ranking.metadata)
            if ranking.category == "repair":
                signals.append(
                    LearningSignal.build(
                        signal_type=LearningSignalType.PREFERRED_REPAIR_STRATEGY,
                        source_pattern_key=ranking.strategy_key,
                        confidence=ranking.confidence,
                        weight=weight,
                        recommendation=ranking.recommendation,
                        evidence_summary={"evidence_count": ranking.evidence_count, "score": ranking.score},
                        metadata=metadata,
                    )
                )
            elif ranking.category == "continuation":
                decision_type = str(metadata.get("decision_type", "")).strip() or ranking.strategy_key.split(":")[1]
                signal_type = (
                    LearningSignalType.DISCOURAGED_RETRY_PATTERN
                    if decision_type == "retry_step" and ranking.score < 0.5
                    else LearningSignalType.PREFERRED_CONTINUATION_DECISION
                )
                signals.append(
                    LearningSignal.build(
                        signal_type=signal_type,
                        source_pattern_key=ranking.strategy_key,
                        confidence=ranking.confidence,
                        weight=weight,
                        recommendation=ranking.recommendation,
                        evidence_summary={"evidence_count": ranking.evidence_count, "score": ranking.score},
                        metadata={**metadata, "decision_type": decision_type},
                    )
                )
            elif ranking.category == "planning":
                selected_tool = str(metadata.get("selected_tool", "")).strip()
                signals.append(
                    LearningSignal.build(
                        signal_type=LearningSignalType.STEP_TEMPLATE_SUCCESS_HINT,
                        source_pattern_key=ranking.strategy_key,
                        confidence=ranking.confidence,
                        weight=weight,
                        recommendation="Insert a bounded validation step after historically sensitive operational actions.",
                        evidence_summary={"evidence_count": ranking.evidence_count, "score": ranking.score},
                        metadata={
                            **metadata,
                            "selected_tool": selected_tool,
                            "suggested_step_type": "validate_result",
                            "require_validation_after_tool": bool(selected_tool),
                        },
                    )
                )
            elif ranking.category == "resume":
                signals.append(
                    LearningSignal.build(
                        signal_type=LearningSignalType.RESUME_CONFIDENCE_HINT,
                        source_pattern_key=ranking.strategy_key,
                        confidence=ranking.confidence,
                        weight=weight,
                        recommendation="Resume confidence is supported by recent checkpoint evidence.",
                        evidence_summary={"evidence_count": ranking.evidence_count, "score": ranking.score},
                        metadata=metadata,
                    )
                )
        for record in records:
            if record.failure_count >= max(policy.min_pattern_samples, 3) and record.success_ratio <= 0.34:
                signals.append(
                    LearningSignal.build(
                        signal_type=LearningSignalType.HIGH_RISK_RECURRENCE_ALERT,
                        source_pattern_key=record.pattern_key,
                        confidence=min(0.95, 0.5 + (record.failure_count / max(1, record.total_count))),
                        weight=min(policy.max_signal_weight, 0.1 + (record.failure_count / max(1, record.total_count)) * 0.2),
                        recommendation="A recurring unsafe failure pattern has been observed. Treat retries conservatively.",
                        evidence_summary={
                            "failure_count": record.failure_count,
                            "success_count": record.success_count,
                            "success_ratio": record.success_ratio,
                        },
                        metadata=dict(record.metadata),
                    )
                )
        deduped: dict[tuple[str, str], LearningSignal] = {}
        for signal in signals:
            key = (signal.signal_type.value, signal.source_pattern_key)
            current = deduped.get(key)
            if current is None or signal.confidence > current.confidence:
                deduped[key] = signal
        return list(deduped.values())

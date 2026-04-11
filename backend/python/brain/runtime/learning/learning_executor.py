from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_ingestor import RuntimeArtifactIngestor
from .evidence_normalizer import EvidenceNormalizer
from .learning_policy import DeterministicLearningPolicy
from .learning_signal_builder import LearningSignalBuilder
from .learning_store import LearningStore
from .models import LearningPolicy, LearningSignal, LearningSnapshot, PatternRecord
from .outcome_aggregator import OutcomeAggregator
from .pattern_registry import PatternRegistry
from .strategy_ranker import StrategyRanker


class LearningExecutor:
    def __init__(self, root: Path, *, policy: LearningPolicy | None = None) -> None:
        self.root = root
        self.policy = policy or DeterministicLearningPolicy.from_env()
        self.store = LearningStore(root)
        self.ingestor = RuntimeArtifactIngestor()
        self.normalizer = EvidenceNormalizer()
        self.registry = PatternRegistry()
        self.aggregator = OutcomeAggregator()
        self.ranker = StrategyRanker()
        self.signal_builder = LearningSignalBuilder()

    def ingest_runtime_artifacts(
        self,
        *,
        action: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        plan: Any = None,
        checkpoint: Any = None,
        summary: Any = None,
        continuation_evaluation: dict[str, Any] | None = None,
        continuation_decision: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.policy.enabled:
            return {"ingested_evidence": 0, "updated_patterns": 0, "signals": []}
        artifacts = self.ingestor.collect(
            action=action,
            result=result,
            plan=plan,
            checkpoint=checkpoint,
            summary=summary,
            continuation_evaluation=continuation_evaluation,
            continuation_decision=continuation_decision,
        )
        updated_records: dict[str, PatternRecord] = {}
        ingested_evidence = 0
        for source_type, payload, context in artifacts:
            evidence = self.normalizer.normalize(source_type=source_type, payload=payload, context=context)
            if evidence is None:
                continue
            ingested_evidence += 1
            self.store.append_evidence(evidence)
            for candidate in self.registry.pattern_records_for(evidence):
                record = self.store.load_pattern(candidate.pattern_key) or candidate
                metadata = dict(candidate.metadata)
                metadata.setdefault("selected_tool", evidence.capability)
                metadata.setdefault("decision_type", evidence.continuation_decision_type)
                metadata.setdefault("plan_health", evidence.metadata.get("plan_health", ""))
                metadata.setdefault("dependency_health", evidence.metadata.get("dependency_health", ""))
                metadata.setdefault("repair_strategy", evidence.metadata.get("repair_strategy", ""))
                metadata.setdefault("failure_class", evidence.failure_class)
                metadata.setdefault("target_file", evidence.metadata.get("target_file", ""))
                record.register_outcome(success=evidence.success, timestamp=evidence.timestamp, metadata=metadata)
                self.store.upsert_pattern(record)
                updated_records[record.pattern_key] = record
        all_records = self.store.load_patterns()
        statistics = self.aggregator.aggregate(all_records)
        rankings = self.ranker.rank(records=all_records, policy=self.policy)
        signals = self.signal_builder.build(rankings=rankings, records=all_records, policy=self.policy)
        for signal in signals:
            self.store.append_signal(signal)
        snapshot = LearningSnapshot.build(
            pattern_count=len(all_records),
            signal_count=len(signals),
            statistics=statistics,
        )
        self.store.save_snapshot(snapshot)
        return {
            "ingested_evidence": ingested_evidence,
            "updated_patterns": len(updated_records),
            "signals": [signal.as_dict() for signal in signals[:12]],
            "statistics": statistics,
            "snapshot": snapshot.as_dict(),
        }

    def advisory_signals_for_planning(self, *, actions: list[dict[str, Any]]) -> list[LearningSignal]:
        tool_names = {str(action.get("selected_tool", "")).strip() for action in actions if str(action.get("selected_tool", "")).strip()}
        signals: list[LearningSignal] = []
        for signal in self.store.load_recent_signals(limit=80):
            required_tool = str(signal.metadata.get("selected_tool", "")).strip()
            if signal.signal_type.value == "step_template_success_hint" and required_tool and required_tool in tool_names:
                signals.append(signal)
        return signals

    def advisory_signals_for_repair(self, *, action: dict[str, Any], result: dict[str, Any]) -> list[LearningSignal]:
        tool_name = str(action.get("selected_tool", "")).strip()
        failure_kind = str((result.get("error_payload") or {}).get("kind", "")).strip() if isinstance(result, dict) else ""
        signals: list[LearningSignal] = []
        for signal in self.store.load_recent_signals(limit=80):
            if signal.signal_type.value != "preferred_repair_strategy":
                continue
            if tool_name and str(signal.metadata.get("selected_tool", "")).strip() not in {"", tool_name}:
                continue
            if failure_kind and str(signal.metadata.get("failure_class", "")).strip() not in {"", failure_kind}:
                continue
            signals.append(signal)
        return signals

    def advisory_signals_for_continuation(self, *, plan: Any = None, result: dict[str, Any] | None = None) -> list[LearningSignal]:
        failure_kind = str((result.get("error_payload") or {}).get("kind", "")).strip() if isinstance(result, dict) else ""
        plan_health = str(getattr(plan, "status", "")).lower() if plan is not None else ""
        signals: list[LearningSignal] = []
        for signal in self.store.load_recent_signals(limit=80):
            if signal.signal_type.value not in {
                "discouraged_retry_pattern",
                "preferred_continuation_decision",
                "high_risk_recurrence_alert",
                "resume_confidence_hint",
            }:
                continue
            metadata_failure = str(signal.metadata.get("failure_class", "")).strip()
            if metadata_failure and failure_kind and metadata_failure != failure_kind:
                continue
            metadata_health = str(signal.metadata.get("plan_health", "")).strip().lower()
            if metadata_health and plan_health and metadata_health != plan_health:
                continue
            signals.append(signal)
        return signals

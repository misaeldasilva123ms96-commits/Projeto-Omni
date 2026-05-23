from __future__ import annotations

from .models import LearningEvidence, PatternRecord


class PatternRegistry:
    def pattern_records_for(self, evidence: LearningEvidence) -> list[PatternRecord]:
        metadata = dict(evidence.metadata)
        records = [
            PatternRecord.build(
                pattern_key=f"execution:{evidence.action_type}:{evidence.capability}:{evidence.subsystem}",
                category="execution",
                metadata=metadata,
            ),
            PatternRecord.build(
                pattern_key=f"execution:{evidence.action_type}:{evidence.capability}:{evidence.subsystem}:{evidence.outcome_class}",
                category="execution_outcome",
                metadata=metadata,
            )
        ]
        if evidence.source_type.value == "repair_receipt":
            strategy = str(metadata.get("repair_strategy", "")).strip() or "unknown"
            target = str(metadata.get("target_file", "")).strip() or "runtime"
            records.append(
                PatternRecord.build(
                    pattern_key=f"repair:{strategy}:{evidence.failure_class or evidence.outcome_class}:{target}",
                    category="repair",
                    metadata=metadata,
                )
            )
        if evidence.source_type.value in {"continuation_decision", "continuation_evaluation"}:
            decision_type = evidence.continuation_decision_type or str(metadata.get("decision_type", "")).strip() or evidence.outcome_class
            plan_health = str(metadata.get("plan_health", "")).strip() or evidence.outcome_class
            dependency_health = str(metadata.get("dependency_health", "")).strip() or "unknown"
            records.append(
                PatternRecord.build(
                    pattern_key=f"continuation:{decision_type}:{plan_health}:{dependency_health}",
                    category="continuation",
                    metadata=metadata,
                )
            )
        if evidence.source_type.value == "plan_checkpoint":
            resume_decision = str(metadata.get("resumable_state", {}).get("resume_decision", "")).strip() or "checkpoint"
            records.append(
                PatternRecord.build(
                    pattern_key=f"resume:{resume_decision}:{evidence.outcome_class}",
                    category="resume",
                    metadata=metadata,
                )
            )
        if evidence.source_type.value == "operational_summary":
            resumability_state = str(metadata.get("resumability_state", "")).strip() or "unknown"
            records.append(
                PatternRecord.build(
                    pattern_key=f"planning:{evidence.outcome_class}:{resumability_state}",
                    category="planning",
                    metadata=metadata,
                )
            )
        return records

from __future__ import annotations

from typing import Any

from .models import EvolutionOpportunity, OpportunityType


class EvolutionOpportunityDetector:
    def detect(
        self,
        *,
        learning_update: dict[str, Any] | None = None,
        orchestration_update: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        continuation_payload: dict[str, Any] | None = None,
    ) -> EvolutionOpportunity | None:
        learning_update = learning_update or {}
        orchestration_update = orchestration_update or {}
        result = result or {}
        continuation_payload = continuation_payload or {}

        signals = learning_update.get("signals", []) if isinstance(learning_update.get("signals", []), list) else []
        statistics = learning_update.get("statistics", {}) if isinstance(learning_update.get("statistics", {}), dict) else {}
        route_decision = (
            ((orchestration_update.get("decision") or {}).get("route"))
            if isinstance(orchestration_update.get("decision"), dict)
            else ""
        )
        continuation_decision = str(continuation_payload.get("decision_type", "")).strip()
        failure_kind = str((result.get("error_payload") or {}).get("kind", "")).strip() if isinstance(result.get("error_payload"), dict) else ""

        if failure_kind and continuation_decision == "escalate_failure":
            return EvolutionOpportunity.build(
                opportunity_type=OpportunityType.REPEATED_ESCALATION_PATTERN,
                title="Repeated escalation pattern detected",
                summary=f"The runtime escalated repeated bounded failures in {failure_kind}, suggesting a governed refinement opportunity.",
                target_subsystem="continuation",
                evidence_ids=self._evidence_ids(result=result),
                evidence_summary={"failure_kind": failure_kind, "continuation_decision": continuation_decision},
                recurrence_count=2,
                metadata={"route": route_decision},
            )

        for signal in signals:
            if not isinstance(signal, dict):
                continue
            signal_type = str(signal.get("signal_type", "")).strip()
            evidence_summary = signal.get("evidence_summary", {}) if isinstance(signal.get("evidence_summary"), dict) else {}
            evidence_count = int(evidence_summary.get("evidence_count", evidence_summary.get("sample_count", 0)) or 0)
            if signal_type == "discouraged_retry_pattern" and evidence_count >= 3:
                return EvolutionOpportunity.build(
                    opportunity_type=OpportunityType.REPEATED_FAILURE_PATTERN,
                    title="Retry pattern underperforming",
                    summary="Observed retry patterns are underperforming consistently enough to justify a governed refinement proposal.",
                    target_subsystem="continuation",
                    evidence_ids=self._signal_ids(signals),
                    evidence_summary=evidence_summary,
                    recurrence_count=evidence_count,
                    metadata={"signal_type": signal_type},
                )
            if signal_type == "step_template_success_hint" and evidence_count >= 3:
                return EvolutionOpportunity.build(
                    opportunity_type=OpportunityType.VALIDATION_INSERTION_PATTERN,
                    title="Validation insertion opportunity detected",
                    summary="Repeated evidence suggests a bounded validation insertion can improve operational outcomes.",
                    target_subsystem="planning",
                    evidence_ids=self._signal_ids(signals),
                    evidence_summary=evidence_summary,
                    recurrence_count=evidence_count,
                    metadata={"signal_type": signal_type},
                )
            if signal_type == "preferred_repair_strategy" and evidence_count >= 3:
                return EvolutionOpportunity.build(
                    opportunity_type=OpportunityType.REPAIR_UNDERPERFORMANCE,
                    title="Repair strategy tuning opportunity detected",
                    summary="Repair evidence suggests a bounded refinement of repair strategy selection or policy tuning.",
                    target_subsystem="self_repair",
                    evidence_ids=self._signal_ids(signals),
                    evidence_summary=evidence_summary,
                    recurrence_count=evidence_count,
                    metadata={"signal_type": signal_type},
                )

        if route_decision in {"analysis_step", "tool_delegation"} and statistics:
            return EvolutionOpportunity.build(
                opportunity_type=OpportunityType.ROUTE_INFERIORITY_PATTERN,
                title="Route performance comparison opportunity detected",
                summary="Recent orchestration evidence suggests bounded route weighting refinement may improve outcomes.",
                target_subsystem="orchestration",
                evidence_ids=self._signal_ids(signals),
                evidence_summary=statistics,
                recurrence_count=max(1, int(statistics.get("total_patterns", 1) or 1)),
                metadata={"route": route_decision},
            )

        return None

    @staticmethod
    def _signal_ids(signals: list[dict[str, Any]]) -> list[str]:
        return [str(signal.get("signal_id", "")).strip() for signal in signals if str(signal.get("signal_id", "")).strip()]

    @staticmethod
    def _evidence_ids(*, result: dict[str, Any]) -> list[str]:
        evidence_ids: list[str] = []
        execution_receipt = result.get("execution_receipt")
        if isinstance(execution_receipt, dict):
            receipt_id = str(execution_receipt.get("receipt_id", "")).strip()
            if receipt_id:
                evidence_ids.append(receipt_id)
        repair_receipt = result.get("repair_receipt")
        if isinstance(repair_receipt, dict):
            receipt_id = str(repair_receipt.get("repair_receipt_id", "")).strip()
            if receipt_id:
                evidence_ids.append(receipt_id)
        return evidence_ids

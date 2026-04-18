from __future__ import annotations

import uuid
from typing import Any

from .controlled_evolution_models import GovernedProposal, ImprovementOpportunity


class ControlledProposalBuilder:
    """Maps bounded opportunities to narrow Phase-39 proposal types (parameter-only)."""

    def build(self, *, opportunity: ImprovementOpportunity, current_tuning: dict[str, Any]) -> GovernedProposal | None:
        ptype = opportunity.recommended_proposal_type
        if ptype == "decomposition_limit_tune":
            cur = int(current_tuning.get("decomposition_max_subtasks", 6) or 6)
            proposed = min(8, cur + 1)
            return GovernedProposal(
                proposal_id=f"prop39-{uuid.uuid4().hex[:14]}",
                opportunity_id=opportunity.opportunity_id,
                proposal_type=ptype,
                scope="runtime_tuning_file",
                target_layer="decomposition",
                change_summary=f"Raise decomposition_max_subtasks from {cur} to {proposed} (capped).",
                risk_class="low",
                validation_requirements=["shape_ok", "bounds_ok", "governance_safe"],
                approval_state="auto_validated_low_risk",
                apply_status="pending",
                monitor_status="pending",
                rollback_status="rollback_ready",
                payload={
                    "key": "decomposition_max_subtasks",
                    "new_value": proposed,
                    "previous_value": cur,
                    "opportunity_category": opportunity.category,
                },
            )
        if ptype == "performance_cache_tune":
            cur = int(current_tuning.get("performance_max_cache_entries", 48) or 48)
            proposed = min(128, max(16, cur + 8))
            return GovernedProposal(
                proposal_id=f"prop39-{uuid.uuid4().hex[:14]}",
                opportunity_id=opportunity.opportunity_id,
                proposal_type=ptype,
                scope="runtime_tuning_file",
                target_layer="performance",
                change_summary=f"Adjust performance_max_cache_entries from {cur} to {proposed}.",
                risk_class="low",
                validation_requirements=["shape_ok", "bounds_ok", "governance_safe"],
                approval_state="auto_validated_low_risk",
                apply_status="pending",
                monitor_status="pending",
                rollback_status="rollback_ready",
                payload={
                    "key": "performance_max_cache_entries",
                    "new_value": proposed,
                    "previous_value": cur,
                    "opportunity_category": opportunity.category,
                },
            )
        if ptype == "strategy_bias_shift":
            cur = float(current_tuning.get("strategy_risk_bias", 0.0) or 0.0)
            proposed = max(-0.15, min(0.15, cur + 0.02))
            return GovernedProposal(
                proposal_id=f"prop39-{uuid.uuid4().hex[:14]}",
                opportunity_id=opportunity.opportunity_id,
                proposal_type=ptype,
                scope="runtime_tuning_file",
                target_layer="strategy",
                change_summary=f"Nudge strategy_risk_bias from {cur} to {proposed} (session advisory only).",
                risk_class="low",
                validation_requirements=["shape_ok", "bounds_ok", "governance_safe"],
                approval_state="auto_validated_low_risk",
                apply_status="pending",
                monitor_status="pending",
                rollback_status="rollback_ready",
                payload={
                    "key": "strategy_risk_bias",
                    "new_value": proposed,
                    "previous_value": cur,
                    "opportunity_category": opportunity.category,
                },
            )
        if ptype == "advisory_routing_preference":
            cur = int(current_tuning.get("coordination_issue_budget", 2) or 2)
            proposed = min(6, cur + 1)
            return GovernedProposal(
                proposal_id=f"prop39-{uuid.uuid4().hex[:14]}",
                opportunity_id=opportunity.opportunity_id,
                proposal_type=ptype,
                scope="runtime_tuning_file",
                target_layer="coordination",
                change_summary=f"Relax coordination advisory budget from {cur} to {proposed} (diagnostic only).",
                risk_class="low",
                validation_requirements=["shape_ok", "bounds_ok", "governance_safe"],
                approval_state="auto_validated_low_risk",
                apply_status="pending",
                monitor_status="pending",
                rollback_status="rollback_ready",
                payload={
                    "key": "coordination_issue_budget",
                    "new_value": proposed,
                    "previous_value": cur,
                    "opportunity_category": opportunity.category,
                },
            )
        if ptype == "observability_threshold_tune":
            cur = int(current_tuning.get("observability_tail_lines", 96) or 96)
            proposed = min(256, cur + 16)
            return GovernedProposal(
                proposal_id=f"prop39-{uuid.uuid4().hex[:14]}",
                opportunity_id=opportunity.opportunity_id,
                proposal_type=ptype,
                scope="runtime_tuning_file",
                target_layer="observability",
                change_summary=f"Increase observability_tail_lines from {cur} to {proposed}.",
                risk_class="low",
                validation_requirements=["shape_ok", "bounds_ok", "governance_safe"],
                approval_state="auto_validated_low_risk",
                apply_status="pending",
                monitor_status="pending",
                rollback_status="rollback_ready",
                payload={
                    "key": "observability_tail_lines",
                    "new_value": proposed,
                    "previous_value": cur,
                    "opportunity_category": opportunity.category,
                },
            )
        if ptype == "compression_cache_tune":
            # Alias to performance cache for Phase 39 narrow scope
            cur = int(current_tuning.get("performance_max_cache_entries", 48) or 48)
            proposed = min(128, max(16, cur + 4))
            return GovernedProposal(
                proposal_id=f"prop39-{uuid.uuid4().hex[:14]}",
                opportunity_id=opportunity.opportunity_id,
                proposal_type="compression_cache_tune",
                scope="runtime_tuning_file",
                target_layer="performance",
                change_summary=f"Compression-related cache cap adjustment {cur} -> {proposed}.",
                risk_class="low",
                validation_requirements=["shape_ok", "bounds_ok", "governance_safe"],
                approval_state="auto_validated_low_risk",
                apply_status="pending",
                monitor_status="pending",
                rollback_status="rollback_ready",
                payload={
                    "key": "performance_max_cache_entries",
                    "new_value": proposed,
                    "previous_value": cur,
                    "opportunity_category": opportunity.category,
                },
            )
        return None

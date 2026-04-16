from __future__ import annotations

from pathlib import Path
from typing import Any

from brain.runtime.control.governance_taxonomy import GovernanceReason, GovernanceSource

from .evolution_models import EvolutionProposalRecord, EvolutionProposalStatus
from .evolution_registry import EvolutionRegistry

_ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    EvolutionProposalStatus.PROPOSED.value: {
        EvolutionProposalStatus.UNDER_REVIEW.value,
        EvolutionProposalStatus.APPROVED.value,
        EvolutionProposalStatus.REJECTED.value,
        EvolutionProposalStatus.DEFERRED.value,
    },
    EvolutionProposalStatus.UNDER_REVIEW.value: {
        EvolutionProposalStatus.APPROVED.value,
        EvolutionProposalStatus.REJECTED.value,
        EvolutionProposalStatus.DEFERRED.value,
    },
    EvolutionProposalStatus.APPROVED.value: set(),
    EvolutionProposalStatus.REJECTED.value: set(),
    EvolutionProposalStatus.DEFERRED.value: set(),
}


class EvolutionService:
    """Governed baseline lifecycle for evolution proposals (no patch application)."""

    def __init__(self, root: Path, *, registry: EvolutionRegistry | None = None) -> None:
        self._registry = registry or EvolutionRegistry(root)

    @property
    def registry(self) -> EvolutionRegistry:
        return self._registry

    def create_proposal(
        self,
        *,
        title: str,
        summary: str,
        target_area: str,
        proposal_type: str,
        rationale: str,
        requested_change: str,
        expected_benefit: str,
        risk_level: str,
        extensions: dict[str, Any] | None = None,
    ) -> EvolutionProposalRecord:
        proposal = EvolutionProposalRecord.build(
            title=title,
            summary=summary,
            target_area=target_area,
            proposal_type=proposal_type,
            rationale=rationale,
            requested_change=requested_change,
            expected_benefit=expected_benefit,
            risk_level=risk_level,
            governance_reason=GovernanceReason.GOVERNANCE_HOLD.value,
            governance_source=GovernanceSource.GOVERNANCE.value,
            extensions=extensions,
        )
        return self._registry.register(proposal)

    def submit_proposal(self, **kwargs: Any) -> EvolutionProposalRecord:
        """Alias for baseline proposal creation."""
        return self.create_proposal(**kwargs)

    def get_proposal(self, proposal_id: str) -> EvolutionProposalRecord | None:
        return self._registry.get(proposal_id)

    def list_proposals(self, *, status: str | None = None, limit: int = 50) -> list[EvolutionProposalRecord]:
        return self._registry.list(status=status, limit=limit)

    def review_proposal(
        self,
        *,
        proposal_id: str,
        approved: bool,
        decision_source: str = "operator_cli",
        reason: str | None = None,
    ) -> EvolutionProposalRecord:
        target = EvolutionProposalStatus.APPROVED if approved else EvolutionProposalStatus.REJECTED
        return self.change_proposal_status(
            proposal_id=proposal_id,
            next_status=target.value,
            decision_source=decision_source,
            reason=reason,
        )

    def change_proposal_status(
        self,
        *,
        proposal_id: str,
        next_status: str,
        decision_source: str = "governance_service",
        reason: str | None = None,
    ) -> EvolutionProposalRecord:
        proposal = self._registry.get(proposal_id)
        if proposal is None:
            raise ValueError("proposal not found")
        target = EvolutionProposalStatus(str(next_status or "").strip().lower())
        allowed = _ALLOWED_STATUS_TRANSITIONS.get(proposal.status, set())
        if target.value not in allowed:
            raise ValueError(
                f"invalid proposal status transition: {proposal.status} -> {target.value}"
            )
        default_reason = GovernanceReason.GOVERNANCE_HOLD.value
        if target == EvolutionProposalStatus.APPROVED:
            default_reason = GovernanceReason.OPERATOR_APPROVE.value
        elif target == EvolutionProposalStatus.REJECTED:
            default_reason = GovernanceReason.POLICY_BLOCK.value
        elif target == EvolutionProposalStatus.DEFERRED:
            default_reason = GovernanceReason.TIMEOUT.value
        proposal.transition_status(
            next_status=target,
            governance_reason=str(reason or default_reason),
            governance_source=str(decision_source or "governance_service"),
        )
        return self._registry.register(proposal)

    def summary(self, *, recent_limit: int = 10) -> dict[str, Any]:
        summary = self._registry.get_summary(recent_limit=recent_limit)
        summary["governed"] = True
        summary["lifecycle"] = {
            "allowed_statuses": [status.value for status in EvolutionProposalStatus],
            "terminal_statuses": [
                EvolutionProposalStatus.APPROVED.value,
                EvolutionProposalStatus.REJECTED.value,
                EvolutionProposalStatus.DEFERRED.value,
            ],
            "auto_apply_enabled": False,
        }
        return summary

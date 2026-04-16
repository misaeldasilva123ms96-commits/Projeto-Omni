from __future__ import annotations

from pathlib import Path
from typing import Any

from brain.runtime.control.governance_taxonomy import GovernanceReason, GovernanceSource

from .evolution_models import EvolutionProposalRecord, EvolutionProposalStatus
from .evolution_registry import EvolutionRegistry
from .evolution_validation import EvolutionValidationOutcome, validate_evolution_proposal

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

    def validate_proposal(
        self,
        *,
        proposal_id: str,
        evaluator: str = "rule_engine",
    ) -> dict[str, Any]:
        proposal = self._registry.get(proposal_id)
        if proposal is None:
            raise ValueError("proposal not found")
        result = validate_evolution_proposal(proposal, evaluator=evaluator)
        payload = result.as_dict()
        proposal.append_validation_result(payload)
        self._registry.register(proposal)
        return payload

    def get_validation_history(self, *, proposal_id: str) -> list[dict[str, Any]]:
        proposal = self._registry.get(proposal_id)
        if proposal is None:
            raise ValueError("proposal not found")
        return [dict(item) for item in proposal.validation_history]

    def promote_validation_result_to_status(
        self,
        *,
        proposal_id: str,
        decision_source: str = "system_validation",
        validation_id: str | None = None,
    ) -> EvolutionProposalRecord:
        proposal = self._registry.get(proposal_id)
        if proposal is None:
            raise ValueError("proposal not found")
        history = list(proposal.validation_history)
        if not history:
            raise ValueError("proposal has no validation history")
        target_validation = None
        if validation_id:
            for item in history:
                if str(item.get("validation_id", "")).strip() == str(validation_id).strip():
                    target_validation = item
                    break
            if target_validation is None:
                raise ValueError("validation result not found")
        else:
            target_validation = history[-1]
        outcome = str(target_validation.get("outcome", "")).strip().lower()
        if outcome == EvolutionValidationOutcome.VALID.value:
            next_status = EvolutionProposalStatus.UNDER_REVIEW.value
            reason = GovernanceReason.GOVERNANCE_HOLD.value
        elif outcome == EvolutionValidationOutcome.INVALID.value:
            next_status = EvolutionProposalStatus.REJECTED.value
            reason = GovernanceReason.POLICY_BLOCK.value
        elif outcome == EvolutionValidationOutcome.RISKY.value:
            next_status = EvolutionProposalStatus.UNDER_REVIEW.value
            reason = GovernanceReason.GOVERNANCE_HOLD.value
            proposal.extensions = dict(proposal.extensions)
            flags = proposal.extensions.get("validation_flags", {})
            if not isinstance(flags, dict):
                flags = {}
            flags["risky_validation"] = True
            flags["last_validation_id"] = str(target_validation.get("validation_id", ""))
            proposal.extensions["validation_flags"] = flags
            self._registry.register(proposal)
        elif outcome == EvolutionValidationOutcome.INCONCLUSIVE.value:
            return proposal
        else:
            raise ValueError(f"unsupported validation outcome: {outcome!r}")
        if proposal.status == next_status:
            return proposal
        return self.change_proposal_status(
            proposal_id=proposal_id,
            next_status=next_status,
            decision_source=decision_source,
            reason=reason,
        )

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
        validation_counts = {outcome.value: 0 for outcome in EvolutionValidationOutcome}
        latest_validation_by_proposal: dict[str, dict[str, Any]] = {}
        proposals_with_recent_validation: list[dict[str, Any]] = []
        for proposal in self._registry.list(limit=max(1, int(recent_limit or 10))):
            latest = proposal.latest_validation if isinstance(proposal.latest_validation, dict) else None
            if latest is None:
                continue
            outcome = str(latest.get("outcome", "")).strip().lower()
            if outcome in validation_counts:
                validation_counts[outcome] += 1
            latest_validation_by_proposal[proposal.proposal_id] = {
                "validation_id": str(latest.get("validation_id", "")),
                "outcome": outcome,
                "score": float(latest.get("score", 0.0) or 0.0),
                "evaluated_at": str(latest.get("evaluated_at", "")),
            }
            proposals_with_recent_validation.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "status": proposal.status,
                    "latest_validation_outcome": outcome,
                    "latest_validation_at": str(latest.get("evaluated_at", "")),
                }
            )
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
        summary["validation_counts"] = validation_counts
        summary["proposals_with_recent_validation"] = proposals_with_recent_validation
        summary["latest_validation_by_proposal"] = latest_validation_by_proposal
        return summary

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OpportunityType(str, Enum):
    REPEATED_FAILURE_PATTERN = "repeated_failure_pattern"
    REPEATED_ESCALATION_PATTERN = "repeated_escalation_pattern"
    REPAIR_UNDERPERFORMANCE = "repair_underperformance"
    VALIDATION_INSERTION_PATTERN = "validation_insertion_pattern"
    ROUTE_INFERIORITY_PATTERN = "route_inferiority_pattern"


class EvolutionProposalType(str, Enum):
    POLICY_TUNING = "policy_tuning"
    TEMPLATE_ADJUSTMENT = "template_adjustment"
    ROUTING_ADJUSTMENT = "routing_adjustment"
    VALIDATION_INSERTION = "validation_insertion"
    BOUNDED_RUNTIME_REFINEMENT = "bounded_runtime_refinement"


class ScopeClass(str, Enum):
    SINGLE_COMPONENT = "single_component"
    SINGLE_SUBSYSTEM = "single_subsystem"
    MULTI_SUBSYSTEM_BLOCKED = "multi_subsystem_blocked"
    OUT_OF_SCOPE = "out_of_scope"


class ScopeDecision(str, Enum):
    ALLOWED = "allowed"
    ALLOWED_WITH_GOVERNANCE = "allowed_with_governance"
    BLOCKED = "blocked"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GovernanceDecisionType(str, Enum):
    REJECTED = "rejected"
    DEFERRED = "deferred"
    APPROVED_FOR_VALIDATION = "approved_for_validation"
    APPROVED_FOR_PROMOTION = "approved_for_promotion"
    BLOCKED_BY_POLICY = "blocked_by_policy"


class PromotionStatus(str, Enum):
    BLOCKED = "blocked"
    NOT_REQUESTED = "not_requested"
    VALIDATED = "validated"
    PROMOTED = "promoted"


@dataclass(slots=True)
class EvolutionOpportunity:
    opportunity_id: str
    opportunity_type: OpportunityType
    title: str
    summary: str
    target_subsystem: str
    evidence_ids: list[str]
    evidence_summary: dict[str, Any]
    recurrence_count: int
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        opportunity_type: OpportunityType,
        title: str,
        summary: str,
        target_subsystem: str,
        evidence_ids: list[str],
        evidence_summary: dict[str, Any],
        recurrence_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> "EvolutionOpportunity":
        return cls(
            opportunity_id=f"evolution-opportunity-{uuid4()}",
            opportunity_type=opportunity_type,
            title=title,
            summary=summary,
            target_subsystem=target_subsystem,
            evidence_ids=evidence_ids,
            evidence_summary=evidence_summary,
            recurrence_count=recurrence_count,
            timestamp=utc_now_iso(),
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["opportunity_type"] = self.opportunity_type.value
        return payload


@dataclass(slots=True)
class ValidationPlan:
    validation_plan_id: str
    proposal_id: str
    validation_modes: list[str]
    targeted_tests: list[str]
    policy_checks: list[str]
    replay_requirements: list[str]
    summary: str

    @classmethod
    def build(
        cls,
        *,
        proposal_id: str,
        validation_modes: list[str],
        targeted_tests: list[str],
        policy_checks: list[str],
        replay_requirements: list[str],
        summary: str,
    ) -> "ValidationPlan":
        return cls(
            validation_plan_id=f"evolution-validation-{uuid4()}",
            proposal_id=proposal_id,
            validation_modes=validation_modes,
            targeted_tests=targeted_tests,
            policy_checks=policy_checks,
            replay_requirements=replay_requirements,
            summary=summary,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvolutionProposal:
    proposal_id: str
    source_opportunity_id: str
    title: str
    summary: str
    target_subsystem: str
    proposal_type: EvolutionProposalType
    scope_class: ScopeClass
    risk_level: RiskLevel
    expected_benefit: str
    expected_affected_artifacts: list[str]
    evidence_summary: dict[str, Any]
    validation_requirements: list[str]
    governance_status: str
    promotion_status: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        source_opportunity_id: str,
        title: str,
        summary: str,
        target_subsystem: str,
        proposal_type: EvolutionProposalType,
        scope_class: ScopeClass,
        risk_level: RiskLevel,
        expected_benefit: str,
        expected_affected_artifacts: list[str],
        evidence_summary: dict[str, Any],
        validation_requirements: list[str],
        governance_status: str,
        promotion_status: str,
        metadata: dict[str, Any] | None = None,
    ) -> "EvolutionProposal":
        return cls(
            proposal_id=f"evolution-proposal-{uuid4()}",
            source_opportunity_id=source_opportunity_id,
            title=title,
            summary=summary,
            target_subsystem=target_subsystem,
            proposal_type=proposal_type,
            scope_class=scope_class,
            risk_level=risk_level,
            expected_benefit=expected_benefit,
            expected_affected_artifacts=expected_affected_artifacts,
            evidence_summary=evidence_summary,
            validation_requirements=validation_requirements,
            governance_status=governance_status,
            promotion_status=promotion_status,
            timestamp=utc_now_iso(),
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["proposal_type"] = self.proposal_type.value
        payload["scope_class"] = self.scope_class.value
        payload["risk_level"] = self.risk_level.value
        return payload


@dataclass(slots=True)
class ScopeAssessment:
    proposal_id: str
    scope_class: ScopeClass
    decision: ScopeDecision
    reason_code: str
    summary: str
    affected_artifacts: list[str]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scope_class"] = self.scope_class.value
        payload["decision"] = self.decision.value
        return payload


@dataclass(slots=True)
class RiskAssessment:
    proposal_id: str
    risk_level: RiskLevel
    reason_code: str
    summary: str
    rollback_available: bool
    factors: list[str]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["risk_level"] = self.risk_level.value
        return payload


@dataclass(slots=True)
class GovernanceDecision:
    governance_decision_id: str
    proposal_id: str
    decision_type: GovernanceDecisionType
    reason_code: str
    reason_summary: str
    approver_type: str
    timestamp: str
    linked_validation_plan_id: str | None
    linked_evidence_ids: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        proposal_id: str,
        decision_type: GovernanceDecisionType,
        reason_code: str,
        reason_summary: str,
        approver_type: str,
        linked_validation_plan_id: str | None,
        linked_evidence_ids: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> "GovernanceDecision":
        return cls(
            governance_decision_id=f"governance-decision-{uuid4()}",
            proposal_id=proposal_id,
            decision_type=decision_type,
            reason_code=reason_code,
            reason_summary=reason_summary,
            approver_type=approver_type,
            timestamp=utc_now_iso(),
            linked_validation_plan_id=linked_validation_plan_id,
            linked_evidence_ids=linked_evidence_ids,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision_type"] = self.decision_type.value
        return payload


@dataclass(slots=True)
class EvolutionPolicy:
    enabled: bool = False
    allow_validation: bool = True
    allow_promotion: bool = False
    max_active_proposals: int = 5
    require_governance_for_medium_and_above: bool = True
    block_critical: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvolutionOutcome:
    opportunity: EvolutionOpportunity | None
    proposal: EvolutionProposal | None
    scope: ScopeAssessment | None
    risk: RiskAssessment | None
    validation_plan: ValidationPlan | None
    governance: GovernanceDecision | None
    promotion_status: PromotionStatus
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "opportunity": self.opportunity.as_dict() if self.opportunity else None,
            "proposal": self.proposal.as_dict() if self.proposal else None,
            "scope": self.scope.as_dict() if self.scope else None,
            "risk": self.risk.as_dict() if self.risk else None,
            "validation_plan": self.validation_plan.as_dict() if self.validation_plan else None,
            "governance": self.governance.as_dict() if self.governance else None,
            "promotion_status": self.promotion_status.value,
            "summary": self.summary,
        }

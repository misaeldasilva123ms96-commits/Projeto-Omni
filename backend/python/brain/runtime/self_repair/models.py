from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RepairEligibilityDecision(str, Enum):
    NOT_REPAIRABLE = "not_repairable"
    REPAIRABLE_WITHIN_SCOPE = "repairable_within_scope"
    REQUIRES_HUMAN_OR_FUTURE_PHASE = "requires_human_or_future_phase"
    BLOCKED_BY_POLICY = "blocked_by_policy"


class RepairStatus(str, Enum):
    BLOCKED = "blocked"
    REJECTED = "rejected"
    VALIDATED = "validated"
    PROMOTED = "promoted"


@dataclass(slots=True)
class FailureEvidence:
    evidence_id: str
    action_id: str
    action_type: str
    subsystem: str
    failure_type: str
    failure_message_summary: str
    error_details: dict[str, Any] = field(default_factory=dict)
    verification_details: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    recurrence_count: int = 0
    session_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    source_receipt_id: str | None = None
    linked_execution_receipt_ids: list[str] = field(default_factory=list)
    capability: str = ""
    selected_agent: str = ""
    source_result_snapshot: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        action_id: str,
        action_type: str,
        subsystem: str,
        failure_type: str,
        failure_message_summary: str,
        **kwargs: Any,
    ) -> "FailureEvidence":
        return cls(
            evidence_id=f"evidence-{uuid4()}",
            action_id=action_id,
            action_type=action_type,
            subsystem=subsystem,
            failure_type=failure_type,
            failure_message_summary=failure_message_summary,
            **kwargs,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepairEligibility:
    decision: RepairEligibilityDecision
    reason_code: str
    summary: str

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        return payload


@dataclass(slots=True)
class CauseHypothesis:
    probable_cause_category: str
    confidence_score: float
    affected_component: str
    repair_strategy_class: str
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepairScope:
    mutation_type: str
    target_files: list[str]
    allowed_root: str
    max_files: int
    max_attempts: int
    validation_required: bool
    within_scope: bool
    reason_code: str
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepairValidationPlan:
    validation_modes: list[str]
    targeted_tests: list[str]
    require_import_validation: bool
    require_receipt_smoke_check: bool
    promotion_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepairProposal:
    proposal_id: str
    evidence_id: str
    cause_category: str
    repair_strategy_class: str
    target_file: str
    proposed_action_summary: str
    expected_fix_outcome: str
    scope_classification: str
    confidence_score: float
    validation_plan: RepairValidationPlan
    promotion_conditions: list[str]
    patch_payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        evidence_id: str,
        cause_category: str,
        repair_strategy_class: str,
        target_file: str,
        proposed_action_summary: str,
        expected_fix_outcome: str,
        scope_classification: str,
        confidence_score: float,
        validation_plan: RepairValidationPlan,
        promotion_conditions: list[str],
        patch_payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> "RepairProposal":
        return cls(
            proposal_id=f"proposal-{uuid4()}",
            evidence_id=evidence_id,
            cause_category=cause_category,
            repair_strategy_class=repair_strategy_class,
            target_file=target_file,
            proposed_action_summary=proposed_action_summary,
            expected_fix_outcome=expected_fix_outcome,
            scope_classification=scope_classification,
            confidence_score=confidence_score,
            validation_plan=validation_plan,
            promotion_conditions=promotion_conditions,
            patch_payload=patch_payload,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validation_plan"] = self.validation_plan.as_dict()
        return payload


@dataclass(slots=True)
class RepairValidationResult:
    passed: bool
    validated_items: list[str]
    error_output_summary: str
    confidence_adjustment: float
    promotion_allowed: bool
    applied_patch: bool = False
    rollback_performed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepairReceipt:
    repair_receipt_id: str
    timestamp: str
    evidence_id: str
    proposal_id: str | None
    eligibility_decision: str
    cause_category: str
    repair_strategy: str
    validation_status: str
    promotion_status: str
    rejection_reason: str
    attempt_count: int
    summary: str
    linked_execution_receipt_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        evidence_id: str,
        proposal_id: str | None,
        eligibility_decision: str,
        cause_category: str,
        repair_strategy: str,
        validation_status: str,
        promotion_status: str,
        rejection_reason: str,
        attempt_count: int,
        summary: str,
        linked_execution_receipt_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "RepairReceipt":
        return cls(
            repair_receipt_id=f"repair-{uuid4()}",
            timestamp=utc_now_iso(),
            evidence_id=evidence_id,
            proposal_id=proposal_id,
            eligibility_decision=eligibility_decision,
            cause_category=cause_category,
            repair_strategy=repair_strategy,
            validation_status=validation_status,
            promotion_status=promotion_status,
            rejection_reason=rejection_reason,
            attempt_count=attempt_count,
            summary=summary,
            linked_execution_receipt_ids=linked_execution_receipt_ids or [],
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepairOutcome:
    status: RepairStatus
    evidence: FailureEvidence
    eligibility: RepairEligibility
    hypothesis: CauseHypothesis | None
    scope: RepairScope | None
    proposal: RepairProposal | None
    validation: RepairValidationResult | None
    receipt: RepairReceipt
    rerun_recommended: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "evidence": self.evidence.as_dict(),
            "eligibility": self.eligibility.as_dict(),
            "hypothesis": self.hypothesis.as_dict() if self.hypothesis else None,
            "scope": self.scope.as_dict() if self.scope else None,
            "proposal": self.proposal.as_dict() if self.proposal else None,
            "validation": self.validation.as_dict() if self.validation else None,
            "receipt": self.receipt.as_dict(),
            "rerun_recommended": self.rerun_recommended,
        }


@dataclass(slots=True)
class SelfRepairPolicy:
    enable_self_repair: bool = False
    allow_promotion: bool = False
    max_files: int = 1
    max_attempts_per_action: int = 1
    max_recurrence: int = 2
    allowed_root: str = "backend/python/brain/runtime"
    allowed_targets: list[str] = field(
        default_factory=lambda: [
            "backend/python/brain/runtime/engineering_tools.py",
            "backend/python/brain/runtime/rust_executor_bridge.py",
            "backend/python/brain/runtime/execution/*.py",
        ]
    )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

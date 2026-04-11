from __future__ import annotations

from .models import CauseHypothesis, FailureEvidence, RepairEligibility, RepairProposal, RepairReceipt, RepairStatus, RepairValidationResult


def build_repair_receipt(
    *,
    evidence: FailureEvidence,
    eligibility: RepairEligibility,
    hypothesis: CauseHypothesis | None,
    proposal: RepairProposal | None,
    validation: RepairValidationResult | None,
    status: RepairStatus,
    summary: str,
) -> RepairReceipt:
    return RepairReceipt.build(
        evidence_id=evidence.evidence_id,
        proposal_id=proposal.proposal_id if proposal else None,
        eligibility_decision=eligibility.decision.value,
        cause_category=hypothesis.probable_cause_category if hypothesis else "not_analyzed",
        repair_strategy=hypothesis.repair_strategy_class if hypothesis else "no_repair_strategy",
        validation_status="passed" if validation and validation.passed else "failed" if validation else "skipped",
        promotion_status=status.value,
        rejection_reason="" if status in {RepairStatus.VALIDATED, RepairStatus.PROMOTED} else eligibility.reason_code,
        attempt_count=evidence.retry_count,
        summary=summary,
        linked_execution_receipt_ids=evidence.linked_execution_receipt_ids,
        metadata={
            "eligibility": eligibility.as_dict(),
            "hypothesis": hypothesis.as_dict() if hypothesis else None,
            "proposal": proposal.as_dict() if proposal else None,
            "validation": validation.as_dict() if validation else None,
        },
    )

from __future__ import annotations

from pathlib import Path

from .failure_analyzer import FailureAnalyzer
from .models import FailureEvidence, RepairEligibility, RepairOutcome, RepairStatus, SelfRepairPolicy
from .repair_policy import RepairPolicyEngine
from .repair_proposer import DeterministicRepairProposer
from .repair_receipt import build_repair_receipt
from .repair_scope import RepairScopeEnforcer
from .repair_validator import RepairValidator


class SelfRepairExecutor:
    def __init__(self, *, workspace_root: Path, policy: SelfRepairPolicy | None = None) -> None:
        self.workspace_root = workspace_root
        self.policy = policy or RepairPolicyEngine.from_env()
        self.policy_engine = RepairPolicyEngine()
        self.analyzer = FailureAnalyzer()
        self.scope_enforcer = RepairScopeEnforcer()
        self.proposer = DeterministicRepairProposer()
        self.validator = RepairValidator()

    def handle_failure(self, *, evidence: FailureEvidence) -> RepairOutcome:
        eligibility = self.policy_engine.evaluate(evidence=evidence, policy=self.policy)
        if eligibility.decision.value != "repairable_within_scope":
            status = RepairStatus.BLOCKED if eligibility.decision.value == "blocked_by_policy" else RepairStatus.REJECTED
            receipt = build_repair_receipt(
                evidence=evidence,
                eligibility=eligibility,
                hypothesis=None,
                proposal=None,
                validation=None,
                status=status,
                summary=eligibility.summary,
            )
            return RepairOutcome(
                status=status,
                evidence=evidence,
                eligibility=eligibility,
                hypothesis=None,
                scope=None,
                proposal=None,
                validation=None,
                receipt=receipt,
                rerun_recommended=False,
            )

        hypothesis = self.analyzer.analyze(evidence)
        proposal = self.proposer.propose(
            workspace_root=self.workspace_root,
            evidence=evidence,
            hypothesis=hypothesis,
            allow_promotion=self.policy.allow_promotion,
        )
        if proposal is None:
            rejected_eligibility = RepairEligibility(
                decision=eligibility.decision,
                reason_code="no_deterministic_repair_template",
                summary="No deterministic bounded repair template matched the failure evidence.",
            )
            receipt = build_repair_receipt(
                evidence=evidence,
                eligibility=rejected_eligibility,
                hypothesis=hypothesis,
                proposal=None,
                validation=None,
                status=RepairStatus.REJECTED,
                summary=rejected_eligibility.summary,
            )
            return RepairOutcome(
                status=RepairStatus.REJECTED,
                evidence=evidence,
                eligibility=rejected_eligibility,
                hypothesis=hypothesis,
                scope=None,
                proposal=None,
                validation=None,
                receipt=receipt,
                rerun_recommended=False,
            )

        scope = self.scope_enforcer.evaluate(
            workspace_root=self.workspace_root,
            proposal=proposal,
            policy=self.policy,
        )
        if not scope.within_scope:
            rejected_eligibility = RepairEligibility(
                decision=eligibility.decision,
                reason_code=scope.reason_code,
                summary=scope.summary,
            )
            receipt = build_repair_receipt(
                evidence=evidence,
                eligibility=rejected_eligibility,
                hypothesis=hypothesis,
                proposal=proposal,
                validation=None,
                status=RepairStatus.REJECTED,
                summary=scope.summary,
            )
            return RepairOutcome(
                status=RepairStatus.REJECTED,
                evidence=evidence,
                eligibility=rejected_eligibility,
                hypothesis=hypothesis,
                scope=scope,
                proposal=proposal,
                validation=None,
                receipt=receipt,
                rerun_recommended=False,
            )

        validation = self.validator.validate(
            workspace_root=self.workspace_root,
            proposal=proposal,
            evidence=evidence,
            policy=self.policy,
        )
        if not validation.passed:
            receipt = build_repair_receipt(
                evidence=evidence,
                eligibility=eligibility,
                hypothesis=hypothesis,
                proposal=proposal,
                validation=validation,
                status=RepairStatus.REJECTED,
                summary=validation.error_output_summary,
            )
            return RepairOutcome(
                status=RepairStatus.REJECTED,
                evidence=evidence,
                eligibility=eligibility,
                hypothesis=hypothesis,
                scope=scope,
                proposal=proposal,
                validation=validation,
                receipt=receipt,
                rerun_recommended=False,
            )

        status = RepairStatus.PROMOTED if validation.promotion_allowed else RepairStatus.VALIDATED
        summary = (
            "Repair was validated and promoted for a bounded replay."
            if status == RepairStatus.PROMOTED
            else "Repair was validated, but promotion remains disabled by policy."
        )
        receipt = build_repair_receipt(
            evidence=evidence,
            eligibility=eligibility,
            hypothesis=hypothesis,
            proposal=proposal,
            validation=validation,
            status=status,
            summary=summary,
        )
        return RepairOutcome(
            status=status,
            evidence=evidence,
            eligibility=eligibility,
            hypothesis=hypothesis,
            scope=scope,
            proposal=proposal,
            validation=validation,
            receipt=receipt,
            rerun_recommended=status == RepairStatus.PROMOTED,
        )

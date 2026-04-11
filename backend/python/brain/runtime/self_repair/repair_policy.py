from __future__ import annotations

import os

from .models import FailureEvidence, RepairEligibility, RepairEligibilityDecision, SelfRepairPolicy


NON_REPAIRABLE_FAILURES = {
    "external_service_outage",
    "network_outage",
    "package_manager_failed",
    "deployment_failed",
    "critical_risk_blocked",
    "high_risk_blocked",
    "risk_above_policy_ceiling",
}

REPAIRABLE_FAILURES = {
    "verification_failed",
    "missing_result_payload",
    "missing_error_payload",
    "invalid_result_shape",
}


class RepairPolicyEngine:
    @staticmethod
    def from_env() -> SelfRepairPolicy:
        return SelfRepairPolicy(
            enable_self_repair=str(os.getenv("OMINI_ENABLE_SELF_REPAIR", "false")).strip().lower() == "true",
            allow_promotion=str(os.getenv("OMINI_SELF_REPAIR_ALLOW_PROMOTION", "false")).strip().lower() == "true",
            max_files=max(1, int(os.getenv("OMINI_SELF_REPAIR_MAX_FILES", "1") or "1")),
            max_attempts_per_action=max(1, int(os.getenv("OMINI_SELF_REPAIR_MAX_ATTEMPTS_PER_ACTION", "1") or "1")),
            max_recurrence=max(1, int(os.getenv("OMINI_SELF_REPAIR_MAX_RECURRENCE", "2") or "2")),
            allowed_root=str(os.getenv("OMINI_SELF_REPAIR_ALLOWED_ROOT", "backend/python/brain/runtime") or "backend/python/brain/runtime"),
        )

    def evaluate(self, *, evidence: FailureEvidence, policy: SelfRepairPolicy) -> RepairEligibility:
        if not policy.enable_self_repair:
            return RepairEligibility(
                decision=RepairEligibilityDecision.BLOCKED_BY_POLICY,
                reason_code="self_repair_disabled",
                summary="Controlled self-repair is disabled by policy.",
            )

        if evidence.retry_count >= policy.max_attempts_per_action:
            return RepairEligibility(
                decision=RepairEligibilityDecision.BLOCKED_BY_POLICY,
                reason_code="max_attempts_exceeded",
                summary="Repair attempts for this action exceeded the configured limit.",
            )

        if evidence.recurrence_count > policy.max_recurrence:
            return RepairEligibility(
                decision=RepairEligibilityDecision.BLOCKED_BY_POLICY,
                reason_code="max_recurrence_exceeded",
                summary="Failure recurrence exceeded the configured self-repair limit.",
            )

        if evidence.failure_type in NON_REPAIRABLE_FAILURES:
            return RepairEligibility(
                decision=RepairEligibilityDecision.REQUIRES_HUMAN_OR_FUTURE_PHASE,
                reason_code="non_repairable_failure_class",
                summary="The failure class is outside the bounded self-repair scope.",
            )

        if evidence.failure_type in REPAIRABLE_FAILURES:
            return RepairEligibility(
                decision=RepairEligibilityDecision.REPAIRABLE_WITHIN_SCOPE,
                reason_code="deterministic_repairable_failure",
                summary="The failure matches a deterministic repairable pattern.",
            )

        return RepairEligibility(
            decision=RepairEligibilityDecision.NOT_REPAIRABLE,
            reason_code="unknown_failure_pattern",
            summary="No bounded deterministic repair policy matched this failure.",
        )

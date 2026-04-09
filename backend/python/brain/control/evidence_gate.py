from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceGateResult:
    enough_evidence: bool
    missing_evidence_types: list[str]
    recommendation: str
    severity: str


class EvidenceGate:
    def evaluate_evidence(
        self,
        *,
        task_type: str,
        risk_level: str,
        available_evidence: dict[str, object] | None,
    ) -> EvidenceGateResult:
        available_evidence = available_evidence or {}
        file_evidence = bool(available_evidence.get("file_evidence"))
        runtime_evidence = bool(available_evidence.get("runtime_evidence"))
        test_evidence = bool(available_evidence.get("test_evidence"))

        if risk_level == "low" and task_type in {"simple_query", "repository_analysis", "reporting"}:
            return EvidenceGateResult(
                enough_evidence=True,
                missing_evidence_types=[],
                recommendation="proceed_read_only",
                severity="info",
            )

        if task_type == "code_mutation":
            missing: list[str] = []
            if not file_evidence:
                missing.append("file_evidence")
            if not runtime_evidence:
                missing.append("runtime_evidence")
            if file_evidence or runtime_evidence:
                return EvidenceGateResult(True, [], "proceed_with_governed_mutation", "info")
            return EvidenceGateResult(
                enough_evidence=False,
                missing_evidence_types=missing,
                recommendation="gather_file_or_runtime_evidence_before_mutation",
                severity="high",
            )

        if task_type == "recovery":
            if runtime_evidence or test_evidence:
                return EvidenceGateResult(True, [], "proceed_with_bounded_recovery", "info")
            return EvidenceGateResult(
                enough_evidence=False,
                missing_evidence_types=["runtime_evidence", "test_evidence"],
                recommendation="collect_runtime_or_test_evidence_before_recovery",
                severity="medium",
            )

        if task_type == "verification":
            return EvidenceGateResult(
                enough_evidence=True,
                missing_evidence_types=[],
                recommendation="proceed_verification",
                severity="info",
            )

        return EvidenceGateResult(
            enough_evidence=True,
            missing_evidence_types=[],
            recommendation="proceed_read_only",
            severity="info",
        )


def evaluate_evidence(
    task_type: str,
    risk_level: str,
    available_evidence: dict[str, object] | None,
) -> EvidenceGateResult:
    return EvidenceGate().evaluate_evidence(
        task_type=task_type,
        risk_level=risk_level,
        available_evidence=available_evidence,
    )

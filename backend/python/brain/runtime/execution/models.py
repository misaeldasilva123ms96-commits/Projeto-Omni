from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ExecutionIntent:
    action_id: str
    action_type: str
    capability: str
    description: str
    input_payload_summary: dict[str, Any]
    expected_outcome: str
    reversible: bool
    target_subsystem: str
    session_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RiskClassification:
    level: RiskLevel
    reason_code: str
    rationale: str

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.value
        return data


@dataclass(slots=True)
class PreflightCheck:
    name: str
    passed: bool
    details: str
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PreflightResult:
    allowed: bool
    checks: list[PreflightCheck]
    reason_code: str
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "checks": [item.as_dict() for item in self.checks],
            "reason_code": self.reason_code,
            "summary": self.summary,
        }


@dataclass(slots=True)
class VerificationResult:
    passed: bool
    reason_code: str
    summary: str
    observed_effects: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionPolicy:
    max_risk: RiskLevel = RiskLevel.HIGH
    allow_high_risk: bool = True
    allow_critical: bool = False
    require_session_for_mutation: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_risk": self.max_risk.value,
            "allow_high_risk": self.allow_high_risk,
            "allow_critical": self.allow_critical,
            "require_session_for_mutation": self.require_session_for_mutation,
        }


@dataclass(slots=True)
class GuardrailDecision:
    allowed: bool
    reason_code: str
    summary: str
    fallback_mode: str = "deny"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExecutionReceipt:
    receipt_id: str
    timestamp: str
    action_id: str
    action_type: str
    risk_level: str
    preflight_status: str
    execution_status: str
    verification_status: str
    retry_count: int
    rollback_status: str
    summary: str
    error_details: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        intent: ExecutionIntent,
        risk_level: RiskLevel,
        preflight_status: str,
        execution_status: str,
        verification_status: str,
        retry_count: int,
        rollback_status: str,
        summary: str,
        error_details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ExecutionReceipt":
        return cls(
            receipt_id=f"receipt-{uuid4()}",
            timestamp=utc_now_iso(),
            action_id=intent.action_id,
            action_type=intent.action_type,
            risk_level=risk_level.value,
            preflight_status=preflight_status,
            execution_status=execution_status,
            verification_status=verification_status,
            retry_count=retry_count,
            rollback_status=rollback_status,
            summary=summary,
            error_details=error_details or {},
            session_id=intent.session_id,
            task_id=intent.task_id,
            run_id=intent.run_id,
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TrustedExecutionResult:
    result: dict[str, Any]
    receipt: ExecutionReceipt
    risk: RiskClassification
    preflight: PreflightResult
    verification: VerificationResult
    guardrail: GuardrailDecision

    def as_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "receipt": self.receipt.as_dict(),
            "risk": self.risk.as_dict(),
            "preflight": self.preflight.as_dict(),
            "verification": self.verification.as_dict(),
            "guardrail": self.guardrail.as_dict(),
        }

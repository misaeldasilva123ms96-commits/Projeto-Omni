from __future__ import annotations

from typing import Any

from .models import ExecutionIntent, ExecutionReceipt, RiskClassification


def build_execution_receipt(
    *,
    intent: ExecutionIntent,
    risk: RiskClassification,
    preflight_status: str,
    execution_status: str,
    verification_status: str,
    retry_count: int,
    rollback_status: str,
    summary: str,
    error_details: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ExecutionReceipt:
    return ExecutionReceipt.build(
        intent=intent,
        risk_level=risk.level,
        preflight_status=preflight_status,
        execution_status=execution_status,
        verification_status=verification_status,
        retry_count=retry_count,
        rollback_status=rollback_status,
        summary=summary,
        error_details=error_details,
        metadata=metadata,
    )

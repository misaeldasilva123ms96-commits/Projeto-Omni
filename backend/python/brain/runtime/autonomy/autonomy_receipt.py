"""Autonomy Receipt — report format for decisions.

Each evaluated decision produces a receipt for audit and traceability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .autonomy_models import AutonomyDecision, DecisionType


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AutonomyReceipt:
    receipt_id: str
    decision_id: str
    decision: str
    risk_level: str
    advisory: bool
    reason: str
    context_summary: str
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AutonomyReceiptLog:
    receipts: list[AutonomyReceipt] = field(default_factory=list)

    def add(self, receipt: AutonomyReceipt) -> None:
        self.receipts.append(receipt)

    def last(self) -> AutonomyReceipt | None:
        if self.receipts:
            return self.receipts[-1]
        return None

    def count(self, *, decision: DecisionType | None = None) -> int:
        if decision is None:
            return len(self.receipts)
        return sum(1 for r in self.receipts if r.decision == decision.value)

    def all_as_dict(self) -> list[dict[str, Any]]:
        return [r.as_dict() for r in self.receipts]


def build_receipt(decision: AutonomyDecision) -> AutonomyReceipt:
    count = len(decision.context_snapshot)
    ctx_summary = f"{count} context fields evaluated"

    from uuid import uuid4

    return AutonomyReceipt(
        receipt_id=str(uuid4()),
        decision_id=decision.decision_id,
        decision=decision.decision.value,
        risk_level=decision.risk_level,
        advisory=decision.advisory,
        reason=decision.reason,
        context_summary=ctx_summary,
        metadata=decision.metadata,
    )

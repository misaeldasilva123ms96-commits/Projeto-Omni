"""Governed Autonomy Controller for Omni runtime decisions.

Evaluates context against policy to produce advisory decisions.
No autonomous write action is executed. All decisions are advisory only.
"""

from __future__ import annotations

import logging
from typing import Any

from .autonomy_escalation import EscalationReport, build_escalation_report
from .autonomy_models import AutonomyContext, AutonomyDecision, DecisionType
from .autonomy_policy import evaluate_policy
from .autonomy_receipt import AutonomyReceipt, AutonomyReceiptLog, build_receipt

logger = logging.getLogger(__name__)

try:
    from brain.memory.runtime_integration import record_governance_event

    _HAS_GOVERNANCE_EVENTS = True
except ImportError:
    _HAS_GOVERNANCE_EVENTS = False
    logger.debug("Memory integration not available; governance events disabled.")


class AutonomyController:
    def __init__(
        self,
        *,
        autonomy_level: str = "supervised",
        max_attempts_per_error: int = 5,
        max_stagnant_attempts: int = 3,
        warn_after_stagnation: int = 3,
        escalate_after_stagnation: int = 5,
        max_total_progressive_cycles: int = 50,
        emit_governance_events: bool = True,
    ) -> None:
        self._autonomy_level = autonomy_level
        self._max_attempts_per_error = max_attempts_per_error
        self._max_stagnant_attempts = max_stagnant_attempts
        self._warn_after_stagnation = warn_after_stagnation
        self._escalate_after_stagnation = escalate_after_stagnation
        self._max_total_progressive_cycles = max_total_progressive_cycles
        self._emit_governance_events = emit_governance_events and _HAS_GOVERNANCE_EVENTS
        self._receipt_log: AutonomyReceiptLog = AutonomyReceiptLog()

    @property
    def autonomy_level(self) -> str:
        return self._autonomy_level

    @property
    def receipt_log(self) -> AutonomyReceiptLog:
        return self._receipt_log

    def _emit_event(self, ctx: AutonomyContext, decision: AutonomyDecision) -> None:
        if not self._emit_governance_events:
            return
        try:
            record_governance_event(
                event_type="autonomy_decision",
                source="autonomy_controller",
                session_id=ctx.session_id,
                run_id=ctx.run_id,
                status=decision.decision.value,
                reason=decision.reason,
                metadata={
                    "decision_id": decision.decision_id,
                    "risk_level": decision.risk_level,
                    "advisory": str(decision.advisory),
                },
            )
        except Exception as exc:
            logger.debug("Failed to emit governance event: %s", exc)

    def decide(self, ctx: AutonomyContext) -> AutonomyDecision:
        decision = evaluate_policy(
            ctx,
            autonomy_level=self._autonomy_level,
            max_attempts_per_error=self._max_attempts_per_error,
            max_stagnant_attempts=self._max_stagnant_attempts,
            escalate_after_stagnation=self._escalate_after_stagnation,
            max_total_progressive_cycles=self._max_total_progressive_cycles,
        )
        receipt = build_receipt(decision)
        self._receipt_log.add(receipt)
        self._emit_event(ctx, decision)
        return decision

    def decide_with_report(
        self,
        ctx: AutonomyContext,
    ) -> tuple[AutonomyDecision, AutonomyReceipt, EscalationReport | None]:
        decision = self.decide(ctx)
        receipt = build_receipt(decision)
        self._receipt_log.add(receipt)
        escalation: EscalationReport | None = None
        if decision.decision == DecisionType.ESCALATE_TO_MISAEL:
            escalation = build_escalation_report(decision, ctx)
        return decision, receipt, escalation

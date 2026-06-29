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

    def _decide_and_record(
        self, ctx: AutonomyContext
    ) -> tuple[AutonomyDecision, AutonomyReceipt]:
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
        return decision, receipt

    def decide(self, ctx: AutonomyContext) -> AutonomyDecision:
        decision, _receipt = self._decide_and_record(ctx)
        return decision

    def get_controller_stats(self) -> dict[str, Any]:
        total = self._receipt_log.count()
        last_receipt = self._receipt_log.last()
        escalation_count = self._receipt_log.count(decision=DecisionType.ESCALATE_TO_MISAEL)

        decisions_by_type: dict[str, int] = {}
        for dt in DecisionType:
            count = self._receipt_log.count(decision=dt)
            if count > 0:
                decisions_by_type[dt.value] = count

        return {
            "total_evaluations": total,
            "decisions_by_type": decisions_by_type,
            "escalation_count": escalation_count,
            "escalation_rate": round(escalation_count / total, 4) if total > 0 else 0.0,
            "abort_safe_count": self._receipt_log.count(decision=DecisionType.ABORT_SAFE),
            "continue_count": self._receipt_log.count(decision=DecisionType.CONTINUE),
            "retry_count": self._receipt_log.count(decision=DecisionType.RETRY),
            "replan_count": self._receipt_log.count(decision=DecisionType.REPLAN),
            "pause_count": self._receipt_log.count(decision=DecisionType.PAUSE),
            "last_decision": last_receipt.decision if last_receipt else None,
            "last_risk_level": last_receipt.risk_level if last_receipt else None,
            "last_updated_at": last_receipt.created_at if last_receipt else None,
            "advisory_mode_enabled": True,
        }

    def decide_with_report(
        self,
        ctx: AutonomyContext,
    ) -> tuple[AutonomyDecision, AutonomyReceipt, EscalationReport | None]:
        decision, receipt = self._decide_and_record(ctx)
        escalation: EscalationReport | None = None
        if decision.decision == DecisionType.ESCALATE_TO_MISAEL:
            escalation = build_escalation_report(decision, ctx)
        return decision, receipt, escalation

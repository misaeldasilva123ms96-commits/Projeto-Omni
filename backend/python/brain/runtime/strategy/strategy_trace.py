from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from brain.runtime.learning.models import utc_now_iso


@dataclass(slots=True)
class StrategyAdaptationTrace:
    """Observability payload for strategy adaptation (Phase 35)."""

    trace_id: str
    session_id: str | None
    run_id: str | None
    selected_mode: str
    selected_path: str
    validation_level: str
    reasoning_depth: int
    risk_tolerance: float
    fallback_mode: str
    fallback_path: str
    signals_used: list[str]
    learning_record_id: str | None
    learning_outcome_class: str | None
    created_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def build(
        cls,
        *,
        session_id: str | None,
        run_id: str | None,
        selected_mode: str,
        selected_path: str,
        validation_level: str,
        reasoning_depth: int,
        risk_tolerance: float,
        fallback_mode: str,
        fallback_path: str,
        signals_used: list[str],
        learning_record_id: str | None,
        learning_outcome_class: str | None,
    ) -> StrategyAdaptationTrace:
        return cls(
            trace_id=f"strat35-{uuid4().hex[:14]}",
            session_id=session_id,
            run_id=run_id,
            selected_mode=selected_mode,
            selected_path=selected_path,
            validation_level=validation_level,
            reasoning_depth=reasoning_depth,
            risk_tolerance=risk_tolerance,
            fallback_mode=fallback_mode,
            fallback_path=fallback_path,
            signals_used=list(signals_used),
            learning_record_id=learning_record_id,
            learning_outcome_class=learning_outcome_class,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "selected_mode": self.selected_mode,
            "selected_path": self.selected_path,
            "validation_level": self.validation_level,
            "reasoning_depth": self.reasoning_depth,
            "risk_tolerance": self.risk_tolerance,
            "fallback_mode": self.fallback_mode,
            "fallback_path": self.fallback_path,
            "signals_used": list(self.signals_used),
            "learning_record_id": self.learning_record_id,
            "learning_outcome_class": self.learning_outcome_class,
            "created_at": self.created_at,
        }

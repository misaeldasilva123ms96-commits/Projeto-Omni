from __future__ import annotations

from pathlib import Path
from typing import Any

from brain.runtime.language.oil_schema import OILRequest
from brain.runtime.learning.runtime_learning_store import RuntimeLearningStore

from .strategy_models import StrategyDecision
from .strategy_selector import StrategySelector


class StrategyEngine:
    """Phase 35 — selects bounded execution strategies using OIL, memory, and prior learning records."""

    def __init__(self, root: Path) -> None:
        self._learning_store = RuntimeLearningStore(root)
        self._selector = StrategySelector()

    def resolve_learning_record(
        self,
        *,
        session_id: str | None,
        explicit_learning_record: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """
        Phase 41.1 — prefer explicit caller payload, else most recent learning row
        for this session. Never falls back to global latest when session_id is set
        (avoids cross-session contamination).
        """
        if explicit_learning_record is not None:
            return explicit_learning_record
        sid = str(session_id or "").strip()
        if sid:
            recent = self._learning_store.read_recent_for_session(sid, limit=1)
            if recent:
                return recent[0]
            return None
        return self._learning_store.read_latest_record()

    def select(
        self,
        *,
        session_id: str | None,
        run_id: str | None,
        message: str,
        oil_request: OILRequest,
        memory_context: dict[str, Any],
        learning_record: dict[str, Any] | None = None,
    ) -> StrategyDecision:
        record = self.resolve_learning_record(session_id=session_id, explicit_learning_record=learning_record)
        return self._selector.select(
            session_id=session_id,
            run_id=run_id,
            message=message,
            oil_request=oil_request,
            memory_context=dict(memory_context or {}),
            learning_record=record,
        )

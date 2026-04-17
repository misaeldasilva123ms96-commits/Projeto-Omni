from __future__ import annotations

from pathlib import Path

from brain.runtime.language.oil_schema import OILRequest
from brain.runtime.learning.runtime_learning_store import RuntimeLearningStore

from .strategy_models import StrategyDecision
from .strategy_selector import StrategySelector


class StrategyEngine:
    """Phase 35 — selects bounded execution strategies using OIL, memory, and prior learning records."""

    def __init__(self, root: Path) -> None:
        self._learning_store = RuntimeLearningStore(root)
        self._selector = StrategySelector()

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
        record = learning_record if learning_record is not None else self._learning_store.read_latest_record()
        return self._selector.select(
            session_id=session_id,
            run_id=run_id,
            message=message,
            oil_request=oil_request,
            memory_context=dict(memory_context or {}),
            learning_record=record,
        )

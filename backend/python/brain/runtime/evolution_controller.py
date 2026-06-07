from __future__ import annotations

from typing import Any

from brain.runtime.evolution import EvolutionExecutor, ControlledEvolutionEngine


class EvolutionController:
    def __init__(
        self,
        evolution_executor: EvolutionExecutor,
        controlled_evolution_engine: ControlledEvolutionEngine,
    ) -> None:
        self.evolution_executor = evolution_executor
        self.controlled_evolution_engine = controlled_evolution_engine

    def load_phase39_tuning(self) -> dict[str, Any]:
        return self.controlled_evolution_engine.store.read()

    def evaluate_turn(
        self,
        *,
        session_id: str,
        evidence: dict[str, Any],
        skip_apply: bool = False,
    ) -> dict[str, Any]:
        try:
            payload = self.controlled_evolution_engine.evaluate_turn(
                session_id=session_id,
                evidence=evidence,
                skip_apply=skip_apply,
            )
            return dict(payload) if isinstance(payload, dict) else {}
        except Exception:
            return {
                "ok": False,
                "error": "controlled_evolution_evaluate_failed",
                "validation_messages": ["controlled_evolution_orchestrator_wrap_failed"],
            }

    def get_evolution_version(self, strategy_state: dict[str, Any]) -> int:
        return int(strategy_state.get("version", 0))

    def evaluate(
        self,
        *,
        learning_update: dict[str, Any] | None = None,
        orchestration_update: dict[str, Any] | None = None,
        result: dict[str, Any],
        goal: Any = None,
    ) -> dict[str, Any]:
        return self.evolution_executor.evaluate(
            learning_update=learning_update,
            orchestration_update=orchestration_update,
            result=result,
            goal=goal,
        )

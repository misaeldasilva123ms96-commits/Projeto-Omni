from __future__ import annotations

import os

from brain.runtime.memory.semantic.models import SemanticFact

from .models import RouteSimulation, RouteType, SimulationContext


class CounterfactualEvaluator:
    MAX_SEMANTIC_DELTA = 0.25

    def __init__(self) -> None:
        self.min_confidence = float(os.getenv("OMINI_MEMORY_MIN_CONFIDENCE_FOR_SEMANTIC_RECALL", "0.6") or 0.6)

    def enrich(
        self,
        *,
        route_simulation: RouteSimulation,
        context: SimulationContext,
        semantic_facts: list[SemanticFact],
    ) -> tuple[RouteSimulation, list[str]]:
        del context
        cumulative_delta = 0.0
        used_facts: list[str] = []
        reasoning_parts: list[str] = []
        for fact in semantic_facts:
            if fact.confidence < self.min_confidence:
                continue
            delta = self._delta_for_fact(route=route_simulation.route, fact=fact)
            if delta == 0.0:
                continue
            allowed_delta = max(-self.MAX_SEMANTIC_DELTA, min(self.MAX_SEMANTIC_DELTA, cumulative_delta + delta))
            delta = allowed_delta - cumulative_delta
            if delta == 0.0:
                continue
            cumulative_delta = allowed_delta
            used_facts.append(fact.fact_id)
            reasoning_parts.append(f"Semantic fact {fact.fact_id} adjusted success by {delta:+.2f}.")
        if cumulative_delta == 0.0:
            return route_simulation, used_facts
        route_simulation.estimated_success_rate = max(0.0, min(1.0, route_simulation.estimated_success_rate + cumulative_delta))
        if cumulative_delta < 0:
            route_simulation.constraint_risk = max(0.0, min(1.0, route_simulation.constraint_risk + abs(cumulative_delta) * 0.5))
        else:
            route_simulation.constraint_risk = max(0.0, min(1.0, route_simulation.constraint_risk - cumulative_delta * 0.25))
        route_simulation.reasoning = f"{route_simulation.reasoning} {' '.join(reasoning_parts)}".strip()
        route_simulation.metadata["semantic_delta"] = cumulative_delta
        return route_simulation, used_facts

    @staticmethod
    def _delta_for_fact(*, route: RouteType, fact: SemanticFact) -> float:
        subject = fact.subject.strip().lower()
        obj = fact.object_value.strip().lower()
        if obj == route.value or subject == route.value:
            return max(-0.12, min(0.12, (fact.confidence - 0.5) * 0.4))
        if obj in {"failed", "blocked"} and subject == route.value:
            return max(-0.12, min(0.0, -fact.confidence * 0.2))
        return 0.0

from __future__ import annotations

from pathlib import Path

from brain.runtime.memory import MemoryFacade

from .counterfactual_evaluator import CounterfactualEvaluator
from .models import RouteSimulation, RouteType, SimulationBasis, SimulationContext, SimulationResult
from .route_forecaster import RouteForecaster
from .simulation_store import SimulationStore


class ActionSimulator:
    def __init__(self, root: Path, *, memory_facade: MemoryFacade | None = None, store: SimulationStore | None = None) -> None:
        self.root = root
        self.memory_facade = memory_facade
        self.store = store or SimulationStore(root)
        self.forecaster = RouteForecaster()
        self.counterfactual = CounterfactualEvaluator()

    def simulate(self, *, context: SimulationContext) -> SimulationResult:
        episodes = self.memory_facade.recall_similar(event_type="continuation_decision", progress=context.current_progress, limit=20) if self.memory_facade is not None else []
        semantic_facts = self.memory_facade.get_semantic_facts("continuation_decision", limit=12) if self.memory_facade is not None else []
        procedural = self.memory_facade.get_procedural_recommendation(context.goal_type, constraint_types=context.active_constraints) if self.memory_facade is not None else None

        routes: list[RouteSimulation] = []
        used_semantic_facts: set[str] = set()
        fallback_to_heuristic = False
        for route in RouteType:
            simulation, used_heuristic = self.forecaster.forecast(route=route, context=context, episodes=episodes)
            fallback_to_heuristic = fallback_to_heuristic or used_heuristic
            simulation, applied_facts = self.counterfactual.enrich(
                route_simulation=simulation,
                context=context,
                semantic_facts=semantic_facts,
            )
            used_semantic_facts.update(applied_facts)
            if procedural is not None and procedural.recommended_route == route.value:
                simulation.estimated_success_rate = min(1.0, simulation.estimated_success_rate + min(0.1, 0.04 + procedural.success_rate * 0.08))
                simulation.confidence = min(0.99, simulation.confidence + 0.05)
                simulation.reasoning = f"{simulation.reasoning} Procedural memory favored this route."
                simulation.metadata["procedural_pattern_id"] = procedural.pattern_id
            routes.append(simulation)

        recommended = self._select_best_route(context=context, routes=routes)
        basis = SimulationBasis(
            episodes_consulted=len(episodes),
            semantic_facts_used=sorted(used_semantic_facts),
            procedural_pattern_used=procedural.as_dict() if procedural is not None else None,
            fallback_to_heuristic=fallback_to_heuristic,
        )
        result = SimulationResult.build(
            recommended_route=recommended.route,
            routes=routes,
            simulation_basis=basis,
            goal_id=context.goal_id,
            metadata={
                "session_id": context.session_id,
                "filtered_high_risk_routes": [route.route.value for route in routes if route.metadata.get("filtered_for_hard_constraints")],
            },
        )
        self.store.append(result)
        return result

    @staticmethod
    def _select_best_route(*, context: SimulationContext, routes: list[RouteSimulation]) -> RouteSimulation:
        filtered = list(routes)
        if context.hard_constraint_active:
            safe_candidates = []
            for route in routes:
                if route.constraint_risk > 0.7:
                    route.metadata["filtered_for_hard_constraints"] = True
                    continue
                safe_candidates.append(route)
            if safe_candidates:
                filtered = safe_candidates
        for route in filtered:
            # Success and goal alignment dominate. Constraint risk is penalized strongly.
            score = (
                route.estimated_success_rate * 0.45
                + route.goal_alignment * 0.35
                - route.constraint_risk * 0.4
                - route.estimated_cost * 0.15
            )
            if route.route == RouteType.PAUSE:
                score -= 0.12
            route.score = score
        filtered.sort(key=lambda item: (item.score, item.confidence, -item.constraint_risk), reverse=True)
        return filtered[0]

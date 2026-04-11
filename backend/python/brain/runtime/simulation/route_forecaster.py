from __future__ import annotations

from brain.runtime.memory.episodic.models import Episode

from .models import RouteSimulation, RouteType, SimulationContext


class RouteForecaster:
    MIN_EPISODES_FOR_ESTIMATE = 3

    def forecast(self, *, route: RouteType, context: SimulationContext, episodes: list[Episode]) -> tuple[RouteSimulation, bool]:
        matching = [episode for episode in episodes if self._route_matches(episode, route)]
        if len(matching) >= self.MIN_EPISODES_FOR_ESTIMATE:
            success_rate = self._success_rate(route=route, episodes=matching)
            constraint_risk = self._constraint_risk(context=context, episodes=matching)
            estimated_cost = self._cost_from_history(episodes=matching)
            confidence = min(0.95, 0.45 + len(matching) * 0.08)
            reasoning = f"History-backed estimate from {len(matching)} similar episodes."
            return (
                RouteSimulation(
                    route=route,
                    estimated_success_rate=success_rate,
                    estimated_cost=estimated_cost,
                    constraint_risk=constraint_risk,
                    goal_alignment=self._goal_alignment(route=route, context=context),
                    supporting_episodes=[episode.episode_id for episode in matching[:8]],
                    reasoning=reasoning,
                    confidence=confidence,
                    metadata={"forecast_mode": "history"},
                ),
                False,
            )

        success_rate, estimated_cost, constraint_risk = self._heuristic_estimate(route=route, context=context)
        return (
            RouteSimulation(
                route=route,
                estimated_success_rate=success_rate,
                estimated_cost=estimated_cost,
                constraint_risk=constraint_risk,
                goal_alignment=self._goal_alignment(route=route, context=context),
                supporting_episodes=[episode.episode_id for episode in matching[:8]],
                reasoning="Heuristic fallback because similar episodic history is below threshold.",
                confidence=0.35,
                metadata={"forecast_mode": "heuristic"},
            ),
            True,
        )

    @staticmethod
    def _route_matches(episode: Episode, route: RouteType) -> bool:
        route_hint = str((episode.metadata or {}).get("decision_type", "")).strip() or str((episode.metadata or {}).get("recommended_route", "")).strip()
        if route_hint:
            return route_hint == route.value
        return str(episode.outcome).strip() == route.value

    @staticmethod
    def _success_rate(*, route: RouteType, episodes: list[Episode]) -> float:
        success_outcomes = {"achieved", "completed", "success", "continue_execution", "complete_plan", "retry", "repair", "replan"}
        if route == RouteType.PAUSE:
            success_outcomes = {"pause", "pause_plan"}
        successes = len([episode for episode in episodes if episode.outcome in success_outcomes])
        return max(0.0, min(1.0, successes / max(len(episodes), 1)))

    @staticmethod
    def _constraint_risk(*, context: SimulationContext, episodes: list[Episode]) -> float:
        failures = len([episode for episode in episodes if episode.outcome in {"failed", "blocked", "escalate_failure"}])
        risk = failures / max(len(episodes), 1)
        if context.hard_constraint_active:
            risk += 0.1
        return max(0.0, min(1.0, risk))

    @staticmethod
    def _cost_from_history(*, episodes: list[Episode]) -> float:
        average_duration = sum(episode.duration_seconds for episode in episodes) / max(len(episodes), 1)
        return max(0.0, min(1.0, average_duration / 30.0))

    @staticmethod
    def _heuristic_estimate(*, route: RouteType, context: SimulationContext) -> tuple[float, float, float]:
        progress = context.current_progress
        if route == RouteType.RETRY:
            return (
                max(0.15, 0.58 - context.retry_count * 0.1),
                0.35,
                min(1.0, 0.32 + context.retry_count * 0.15 + (0.15 if context.hard_constraint_active else 0.0)),
            )
        if route == RouteType.REPAIR:
            return (
                max(0.2, 0.64 - context.repair_count * 0.08),
                0.48,
                min(1.0, 0.28 + context.repair_count * 0.12 + (0.18 if context.hard_constraint_active else 0.0)),
            )
        if route == RouteType.REPLAN:
            return (
                max(0.2, 0.52 - progress * 0.12),
                min(1.0, 0.5 + progress * 0.25),
                min(1.0, 0.26 + (0.1 if context.hard_constraint_active else 0.0)),
            )
        pause_success = 0.18
        if context.hard_constraint_active or context.last_outcome in {"dependency_missing", "manual_review_required"}:
            pause_success = 0.3
        return (
            pause_success,
            0.08,
            0.08,
        )

    @staticmethod
    def _goal_alignment(*, route: RouteType, context: SimulationContext) -> float:
        goal_type = context.goal_type
        if not context.goal_present:
            if route == RouteType.PAUSE:
                return 0.35
            return 0.5

        if route == RouteType.PAUSE:
            base = 0.18
            if context.hard_constraint_active or context.last_outcome in {"dependency_missing", "manual_review_required"}:
                base = 0.38
            if goal_type in {"safety", "governance"}:
                base += 0.12
            return max(0.0, min(0.5, base))
        if route == RouteType.RETRY:
            base = 0.72 - context.retry_count * 0.12
            if goal_type in {"repair", "execution"}:
                base += 0.05
            return max(0.0, min(1.0, base))
        if route == RouteType.REPAIR:
            base = 0.78 - context.repair_count * 0.1
            if goal_type in {"repair", "execution"}:
                base += 0.05
            return max(0.0, min(1.0, base))
        base = 0.62 - context.current_progress * 0.35
        if goal_type in {"planning"}:
            base += 0.08
        return max(0.0, min(1.0, base))

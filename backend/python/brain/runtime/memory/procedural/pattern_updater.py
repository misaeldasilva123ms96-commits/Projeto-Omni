from __future__ import annotations

from uuid import uuid4

from brain.runtime.memory.episodic.models import Episode
from brain.runtime.memory.semantic.models import SemanticFact

from .models import ProceduralPattern, utc_now_iso


class PatternUpdater:
    def update_from_episode(self, *, episode: Episode) -> ProceduralPattern | None:
        goal_type = str((episode.metadata or {}).get("goal_type", "")).strip()
        recommended_route = str((episode.metadata or {}).get("recommended_route", "")).strip() or str(
            (episode.metadata or {}).get("decision_type", "")
        ).strip()
        if not goal_type or not recommended_route:
            return None
        success = episode.outcome in {"achieved", "completed", "success", "continue_execution", "complete_plan"}
        return ProceduralPattern(
            pattern_id=f"procedural-pattern-{uuid4()}",
            name=f"{goal_type}:{recommended_route}",
            description=f"Recommended route {recommended_route} for goal type {goal_type}.",
            applicable_goal_types=[goal_type],
            applicable_constraint_types=[str(item) for item in episode.constraints_active if str(item).strip()],
            recommended_route=recommended_route,
            success_rate=1.0 if success else 0.0,
            sample_size=1,
            last_updated=utc_now_iso(),
            metadata={"source_episode_id": episode.episode_id},
        )

    def reinforce(
        self,
        *,
        existing: ProceduralPattern,
        episode: Episode | None = None,
        fact: SemanticFact | None = None,
    ) -> ProceduralPattern:
        sample_size = existing.sample_size
        weighted_success = existing.success_rate * sample_size
        if episode is not None:
            sample_size += 1
            weighted_success += 1.0 if episode.outcome in {"achieved", "completed", "success", "continue_execution", "complete_plan"} else 0.0
        if fact is not None:
            fact_sample_size = max(1, int((fact.metadata or {}).get("sample_size", 1) or 1))
            sample_size += fact_sample_size
            weighted_success += fact.confidence * fact_sample_size
        existing.sample_size = sample_size
        existing.success_rate = max(0.0, min(1.0, weighted_success / max(sample_size, 1)))
        existing.last_updated = utc_now_iso()
        if fact is not None:
            existing.metadata["semantic_fact_id"] = fact.fact_id
        return existing

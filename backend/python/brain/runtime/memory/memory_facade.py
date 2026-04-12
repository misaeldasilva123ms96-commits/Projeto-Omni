from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .episodic import EpisodeBuilder, EpisodicStore
from .memory_sync import MemorySync
from .procedural import PatternUpdater, ProceduralRegistry
from .semantic import FactConsolidator, SemanticIndex
from .working import WorkingMemory

if TYPE_CHECKING:
    from brain.runtime.goals import GoalContext


class MemoryFacade:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._closed = False
        self.working = WorkingMemory(root)
        self.episodic = EpisodicStore(root)
        self.semantic = SemanticIndex(root)
        self.procedural = ProceduralRegistry(root)
        self.episode_builder = EpisodeBuilder()
        self.fact_consolidator = FactConsolidator()
        self.pattern_updater = PatternUpdater()
        self.sync = MemorySync(root)

    def start_new_session(
        self,
        *,
        session_id: str,
        goal_id: str | None = None,
        active_plan_id: str | None = None,
        ttl_seconds: int = 3600,
    ):
        return self.working.start_new_session(
            session_id=session_id,
            goal_id=goal_id,
            active_plan_id=active_plan_id,
            ttl_seconds=ttl_seconds,
        )

    def close_session(self):
        return self.working.close_session()

    def reset_session(self):
        return self.working.reset_session()

    def set_active_goal(
        self,
        *,
        session_id: str,
        goal_id: str,
        active_plan_id: str | None = None,
        goal_context: "GoalContext | None" = None,
    ):
        state = self.working.set_active_goal(
            session_id=session_id,
            goal_id=goal_id,
            active_plan_id=active_plan_id,
            active_constraints=list(goal_context.active_constraints) if goal_context is not None else [],
        )
        self.sync.export_async(
            payload={
                "artifact_type": "working_goal_activation",
                "session_id": session_id,
                "goal_id": goal_id,
                "active_plan_id": active_plan_id,
            }
        )
        return state

    def record_event(
        self,
        *,
        event_type: str,
        description: str,
        outcome: str = "",
        progress_score: float | None = None,
        evidence_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        event = self.working.record_event(
            event_type=event_type,
            description=description,
            outcome=outcome,
            progress_score=progress_score,
            evidence_ids=evidence_ids,
            metadata=metadata,
        )
        self.sync.export_async(payload={"artifact_type": "working_event", "payload": event.as_dict()})
        return event

    def update_progress(self, progress_score: float):
        return self.working.update_progress(progress_score)

    def close_goal_episode(
        self,
        *,
        outcome: str,
        description: str,
        event_type: str = "goal_resolution",
        evidence_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        coordination_trace_id: str | None = None,
        subgoal_id: str | None = None,
        duration_seconds: float = 0.0,
    ):
        snapshot = self.working.snapshot()
        merged_metadata = dict(metadata or {})
        if coordination_trace_id:
            merged_metadata["coordination_trace_id"] = coordination_trace_id
        episode = self.episode_builder.build(
            working_state=snapshot,
            goal_id=snapshot.goal_id,
            outcome=outcome,
            description=description,
            event_type=event_type,
            progress_at_start=snapshot.current_progress,
            progress_at_end=snapshot.current_progress,
            evidence_ids=evidence_ids,
            subgoal_id=subgoal_id,
            duration_seconds=duration_seconds,
            metadata=merged_metadata,
        )
        if episode is None:
            return None
        self.episodic.save_episode(episode)
        consolidated = self.fact_consolidator.consolidate(episodes=self.episodic.recent(limit=200))
        for fact in consolidated:
            self.semantic.upsert_fact(fact)
            self.sync.export_async(payload={"artifact_type": "semantic_fact", "payload": fact.as_dict()})
        procedural_pattern = self.pattern_updater.update_from_episode(episode=episode)
        if procedural_pattern is not None:
            existing = self.procedural.best_pattern_for(
                goal_type=procedural_pattern.applicable_goal_types[0],
                constraint_types=procedural_pattern.applicable_constraint_types,
            )
            if existing and existing.name == procedural_pattern.name:
                procedural_pattern = self.pattern_updater.reinforce(existing=existing, episode=episode)
            self.procedural.upsert(procedural_pattern)
        self.sync.export_async(payload={"artifact_type": "episode", "payload": episode.as_dict()})
        return episode

    def recall_similar(self, *, event_type: str, progress: float, limit: int = 5):
        return self.episodic.query_similar_context(
            event_type=event_type,
            progress_min=max(0.0, progress - 0.2),
            progress_max=min(1.0, progress + 0.2),
            limit=limit,
        )

    def get_procedural_recommendation(self, goal_type: str, *, constraint_types: list[str] | None = None):
        return self.procedural.best_pattern_for(goal_type=goal_type, constraint_types=constraint_types)

    def get_semantic_facts(self, subject: str, *, limit: int = 10):
        return self.semantic.get_facts(subject=subject, limit=limit)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.episodic.close()
        self.semantic.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            return

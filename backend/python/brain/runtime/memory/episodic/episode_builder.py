from __future__ import annotations

from uuid import uuid4

from brain.runtime.memory.working.models import WorkingMemoryState

from .models import Episode, utc_now_iso


class EpisodeBuilder:
    def build(
        self,
        *,
        working_state: WorkingMemoryState,
        goal_id: str | None,
        outcome: str,
        description: str,
        event_type: str,
        progress_at_start: float,
        progress_at_end: float,
        evidence_ids: list[str] | None = None,
        subgoal_id: str | None = None,
        duration_seconds: float = 0.0,
        metadata: dict[str, object] | None = None,
    ) -> Episode | None:
        if not goal_id:
            return None
        return Episode(
            episode_id=f"episode-{uuid4()}",
            goal_id=goal_id,
            subgoal_id=subgoal_id,
            session_id=str(working_state.session_id or ""),
            description=description,
            event_type=event_type,
            outcome=outcome,
            progress_at_start=max(0.0, min(1.0, progress_at_start)),
            progress_at_end=max(0.0, min(1.0, progress_at_end)),
            constraints_active=list(working_state.active_constraints),
            evidence_ids=list(evidence_ids or []),
            duration_seconds=max(0.0, duration_seconds),
            created_at=utc_now_iso(),
            metadata={
                "recent_events": [event.as_dict() for event in working_state.recent_events[-10:]],
                **dict(metadata or {}),
            },
        )

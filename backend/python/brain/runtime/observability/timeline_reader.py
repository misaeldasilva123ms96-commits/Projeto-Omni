from __future__ import annotations

from pathlib import Path

from brain.runtime.memory.working.models import WorkingMemoryState

from ._reader_utils import read_json_resilient
from .models import TimelineEvent


class TimelineReader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".logs" / "fusion-runtime" / "memory" / "working_memory.json"

    def read_state(self) -> WorkingMemoryState | None:
        payload = read_json_resilient(self.path)
        if not isinstance(payload, dict):
            return None
        try:
            return WorkingMemoryState.from_dict(payload)
        except Exception:
            return None

    def read_recent_events(self, *, limit: int = 25) -> list[TimelineEvent]:
        state = self.read_state()
        if state is None:
            return []
        events = state.recent_events[-max(1, limit) :]
        return [
            TimelineEvent(
                event_id=event.event_id,
                event_type=event.event_type,
                description=event.description,
                outcome=event.outcome,
                progress_score=event.progress_score,
                timestamp=event.timestamp,
                evidence_ids=list(event.evidence_ids),
                metadata=dict(event.metadata),
            )
            for event in events
        ]

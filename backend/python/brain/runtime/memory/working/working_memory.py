from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from uuid import uuid4

from .models import WorkingMemoryEvent, WorkingMemoryState, utc_now_iso


class WorkingMemory:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.base_dir = root / ".logs" / "fusion-runtime" / "memory"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "working_memory.json"
        self._lock = threading.RLock()
        self._event_window = max(5, int(os.getenv("OMINI_MEMORY_WORKING_EVENT_WINDOW", "50") or 50))
        self.state = self._load()

    def start_new_session(
        self,
        *,
        session_id: str,
        goal_id: str | None = None,
        active_plan_id: str | None = None,
        ttl_seconds: int = 3600,
    ) -> WorkingMemoryState:
        with self._lock:
            self.state = WorkingMemoryState(
                session_id=session_id,
                goal_id=goal_id,
                active_plan_id=active_plan_id,
                recent_events=[],
                active_constraints=[],
                current_progress=0.0,
                opened_at=utc_now_iso(),
                closed_at=None,
                ttl_seconds=ttl_seconds,
                status="active",
            )
            self.flush()
            return self.snapshot()

    def close_session(self) -> WorkingMemoryState:
        with self._lock:
            self.state.closed_at = utc_now_iso()
            self.state.status = "closed"
            self.flush()
            return self.snapshot()

    def reset_session(self) -> WorkingMemoryState:
        with self._lock:
            self.state = WorkingMemoryState()
            self.flush()
            return self.snapshot()

    def set_active_goal(
        self,
        *,
        session_id: str,
        goal_id: str,
        active_plan_id: str | None = None,
        active_constraints: list[str] | None = None,
    ) -> WorkingMemoryState:
        with self._lock:
            if self.state.session_id != session_id or self.state.status != "active":
                self.start_new_session(session_id=session_id, goal_id=goal_id, active_plan_id=active_plan_id)
            self.state.goal_id = goal_id
            self.state.active_plan_id = active_plan_id
            self.state.active_constraints = list(active_constraints or [])
            self.flush()
            return self.snapshot()

    def record_event(
        self,
        *,
        event_type: str,
        description: str,
        outcome: str = "",
        progress_score: float | None = None,
        evidence_ids: list[str] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> WorkingMemoryEvent:
        with self._lock:
            event = WorkingMemoryEvent(
                event_id=f"working-event-{uuid4()}",
                event_type=event_type,
                description=description,
                outcome=outcome,
                progress_score=max(0.0, min(1.0, progress_score if progress_score is not None else self.state.current_progress)),
                evidence_ids=list(evidence_ids or []),
                metadata=dict(metadata or {}),
            )
            self.state.recent_events.append(event)
            self.state.recent_events = self.state.recent_events[-self._event_window:]
            if progress_score is not None:
                self.state.current_progress = event.progress_score
            self.flush()
            return event

    def update_progress(self, progress_score: float) -> WorkingMemoryState:
        with self._lock:
            self.state.current_progress = max(0.0, min(1.0, float(progress_score)))
            self.flush()
            return self.snapshot()

    def snapshot(self) -> WorkingMemoryState:
        with self._lock:
            return WorkingMemoryState.from_dict(self.state.as_dict())

    def flush(self) -> None:
        with self._lock:
            self.path.write_text(json.dumps(self.state.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> WorkingMemoryState:
        if not self.path.exists():
            return WorkingMemoryState()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return WorkingMemoryState.from_dict(payload)

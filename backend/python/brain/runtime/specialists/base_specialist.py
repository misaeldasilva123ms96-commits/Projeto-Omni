from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any

from brain.runtime.goals import Goal, GoalStore
from brain.runtime.memory import MemoryFacade
from brain.runtime.simulation import SimulationStore


class BaseSpecialist(ABC):
    def __init__(
        self,
        *,
        root: Path,
        goal_store: GoalStore | None = None,
        memory_facade: MemoryFacade | None = None,
        simulation_store: SimulationStore | None = None,
    ) -> None:
        self.root = root
        self.goal_store = goal_store or GoalStore(root)
        self.memory_facade = memory_facade
        self.simulation_store = simulation_store

    def lookup_goal(self, goal_id: str | None) -> Goal | None:
        if not goal_id:
            return None
        return self.goal_store.get_by_id(goal_id)

    def recall_memory(self, *, event_type: str, progress: float, limit: int = 5) -> list[Any]:
        if self.memory_facade is None:
            return []
        return list(self.memory_facade.recall_similar(event_type=event_type, progress=progress, limit=limit))

    def latest_simulation_payload(self, goal_id: str | None) -> dict[str, Any] | None:
        if self.simulation_store is None or not goal_id:
            return None
        for payload in reversed(self.simulation_store.load_recent(limit=10)):
            if payload.get("goal_id") == goal_id:
                return payload
        return None

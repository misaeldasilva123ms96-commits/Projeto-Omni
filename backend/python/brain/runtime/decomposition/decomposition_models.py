from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SubTask:
    id: str
    description: str
    parent_step_id: str
    depends_on: list[str]
    type: str
    depth: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "parent_step_id": self.parent_step_id,
            "depends_on": list(self.depends_on),
            "type": self.type,
            "depth": self.depth,
        }


@dataclass(slots=True)
class DecompositionTrace:
    trace_id: str
    plan_id: str
    reasoning_link: str
    subtask_count: int
    max_depth_observed: int
    truncated: bool
    max_depth_reached: bool
    warnings: list[str]
    strategy_trace_link: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DecompositionResult:
    subtasks: list[SubTask]
    trace: DecompositionTrace

    def as_dict(self) -> dict[str, Any]:
        return {
            "subtasks": [s.as_dict() for s in self.subtasks],
            "trace": self.trace.as_dict(),
        }

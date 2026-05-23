from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RouteType(str, Enum):
    RETRY = "retry"
    REPAIR = "repair"
    REPLAN = "replan"
    PAUSE = "pause"


@dataclass(slots=True)
class RouteSimulation:
    route: RouteType
    estimated_success_rate: float
    estimated_cost: float
    constraint_risk: float
    goal_alignment: float
    supporting_episodes: list[str]
    reasoning: str
    confidence: float
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["route"] = self.route.value
        return payload


@dataclass(slots=True)
class SimulationBasis:
    episodes_consulted: int
    semantic_facts_used: list[str]
    procedural_pattern_used: dict[str, Any] | None
    fallback_to_heuristic: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SimulationContext:
    goal_id: str | None
    goal_description: str
    goal_type: str
    current_progress: float
    last_action: dict[str, Any]
    last_outcome: str
    active_constraints: list[str]
    retry_count: int
    repair_count: int
    session_id: str | None
    hard_constraint_active: bool = False
    goal_present: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SimulationResult:
    simulation_id: str
    recommended_route: RouteType
    routes: list[RouteSimulation]
    simulation_basis: SimulationBasis
    goal_id: str | None
    simulated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        *,
        recommended_route: RouteType,
        routes: list[RouteSimulation],
        simulation_basis: SimulationBasis,
        goal_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> "SimulationResult":
        return cls(
            simulation_id=f"simulation-{uuid4()}",
            recommended_route=recommended_route,
            routes=routes,
            simulation_basis=simulation_basis,
            goal_id=goal_id,
            simulated_at=utc_now_iso(),
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "recommended_route": self.recommended_route.value,
            "routes": [route.as_dict() for route in self.routes],
            "simulation_basis": self.simulation_basis.as_dict(),
            "goal_id": self.goal_id,
            "simulated_at": self.simulated_at,
            "metadata": dict(self.metadata),
        }

    def route_for(self, route: RouteType) -> RouteSimulation | None:
        for candidate in self.routes:
            if candidate.route == route:
                return candidate
        return None

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._reader_utils import read_tail_jsonl
from .models import RouteSnapshot, SimulationSnapshot


class SimulationReader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / ".logs" / "fusion-runtime" / "simulation" / "simulation_log.jsonl"

    def read_latest_simulation(self, *, goal_id: str | None = None) -> SimulationSnapshot | None:
        simulations = self.read_recent_simulations(limit=10, goal_id=goal_id)
        return simulations[-1] if simulations else None

    def read_recent_simulations(self, *, limit: int = 10, goal_id: str | None = None) -> list[SimulationSnapshot]:
        payloads = read_tail_jsonl(self.path, limit=max(limit * 2, limit))
        simulations: list[SimulationSnapshot] = []
        for payload in payloads:
            snapshot = self._to_snapshot(payload)
            if snapshot is None:
                continue
            if goal_id and snapshot.goal_id != goal_id:
                continue
            simulations.append(snapshot)
        return simulations[-max(1, limit) :]

    def _to_snapshot(self, payload: dict[str, Any]) -> SimulationSnapshot | None:
        simulation_id = str(payload.get("simulation_id", "")).strip()
        if not simulation_id:
            return None
        routes: list[RouteSnapshot] = []
        for raw_route in payload.get("routes", []):
            if not isinstance(raw_route, dict):
                continue
            routes.append(
                RouteSnapshot(
                    route=str(raw_route.get("route", "")),
                    estimated_success_rate=float(raw_route.get("estimated_success_rate", 0.0) or 0.0),
                    estimated_cost=float(raw_route.get("estimated_cost", 0.0) or 0.0),
                    constraint_risk=float(raw_route.get("constraint_risk", 0.0) or 0.0),
                    goal_alignment=float(raw_route.get("goal_alignment", 0.0) or 0.0),
                    confidence=float(raw_route.get("confidence", 0.0) or 0.0),
                    score=float(raw_route.get("score", 0.0) or 0.0),
                    reasoning=str(raw_route.get("reasoning", "")),
                    supporting_episodes=[str(item) for item in raw_route.get("supporting_episodes", []) if str(item).strip()],
                    metadata=dict(raw_route.get("metadata", {}) or {}),
                )
            )
        return SimulationSnapshot(
            simulation_id=simulation_id,
            goal_id=str(payload.get("goal_id")) if payload.get("goal_id") else None,
            recommended_route=str(payload.get("recommended_route", "")),
            simulated_at=str(payload.get("simulated_at", "")),
            routes=routes,
            basis=dict(payload.get("simulation_basis", {}) or {}),
            metadata=dict(payload.get("metadata", {}) or {}),
        )

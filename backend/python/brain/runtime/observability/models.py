from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class GoalCriterionSnapshot:
    description: str
    criterion_type: str
    required: bool
    weight: float
    status: str = "unknown"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SubGoalSnapshot:
    subgoal_id: str
    description: str
    status: str
    order: int
    depends_on_subgoal_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GoalSnapshot:
    goal_id: str
    description: str
    intent: str
    status: str
    priority: int
    progress_score: float | None
    active_constraints: list[str]
    success_criteria: list[GoalCriterionSnapshot]
    subgoals: list[SubGoalSnapshot]
    created_at: str
    resolved_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["success_criteria"] = [item.as_dict() for item in self.success_criteria]
        payload["subgoals"] = [item.as_dict() for item in self.subgoals]
        return payload


@dataclass(slots=True)
class TimelineEvent:
    event_id: str
    event_type: str
    description: str
    outcome: str
    progress_score: float
    timestamp: str
    evidence_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpecialistDecisionSnapshot:
    decision_id: str
    specialist_type: str
    status: str
    reasoning: str
    confidence: float
    simulation_id: str | None
    decided_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GovernanceVerdictSnapshot:
    decision_id: str
    verdict: str
    risk_level: str
    blocked_reasons: list[str]
    violations: list[str]
    reasoning: str
    confidence: float
    decided_at: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TraceSnapshot:
    trace_id: str
    goal_id: str | None
    session_id: str | None
    final_outcome: str
    started_at: str
    completed_at: str | None
    decisions: list[SpecialistDecisionSnapshot] = field(default_factory=list)
    governance_verdicts: list[GovernanceVerdictSnapshot] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decisions"] = [item.as_dict() for item in self.decisions]
        payload["governance_verdicts"] = [item.as_dict() for item in self.governance_verdicts]
        return payload


@dataclass(slots=True)
class RouteSnapshot:
    route: str
    estimated_success_rate: float
    estimated_cost: float
    constraint_risk: float
    goal_alignment: float
    confidence: float
    score: float
    reasoning: str
    supporting_episodes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SimulationSnapshot:
    simulation_id: str
    goal_id: str | None
    recommended_route: str
    simulated_at: str
    routes: list[RouteSnapshot] = field(default_factory=list)
    basis: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["routes"] = [item.as_dict() for item in self.routes]
        return payload


@dataclass(slots=True)
class EpisodeSnapshot:
    episode_id: str
    goal_id: str
    subgoal_id: str | None
    session_id: str
    description: str
    event_type: str
    outcome: str
    progress_at_start: float
    progress_at_end: float
    duration_seconds: float
    created_at: str
    evidence_ids: list[str] = field(default_factory=list)
    constraints_active: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SemanticFactSnapshot:
    fact_id: str
    subject: str
    predicate: str
    object_value: str
    confidence: float
    source_episode_ids: list[str]
    goal_types: list[str]
    created_at: str
    last_reinforced_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["object"] = payload.pop("object_value")
        return payload


@dataclass(slots=True)
class ProceduralPatternSnapshot:
    pattern_id: str
    name: str
    description: str
    applicable_goal_types: list[str]
    applicable_constraint_types: list[str]
    recommended_route: str
    success_rate: float
    sample_size: int
    last_updated: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ObservabilitySnapshot:
    generated_at: str
    goal: GoalSnapshot | None
    goal_history: list[GoalSnapshot]
    timeline: list[TimelineEvent]
    latest_trace: TraceSnapshot | None
    recent_traces: list[TraceSnapshot]
    latest_simulation: SimulationSnapshot | None
    recent_simulations: list[SimulationSnapshot]
    recent_episodes: list[EpisodeSnapshot]
    semantic_facts: list[SemanticFactSnapshot]
    active_procedural_pattern: ProceduralPatternSnapshot | None
    recent_procedural_updates: list[ProceduralPatternSnapshot]
    recent_learning_signals: list[dict[str, Any]]
    pending_evolution_proposal_count: int
    recent_evolution_proposals: list[dict[str, Any]]
    engine_adoption: dict[str, Any] | None = None
    active_runs: list[dict[str, Any]] = field(default_factory=list)
    governance_summary: dict[str, Any] = field(default_factory=dict)
    resolution_counts: dict[str, int] = field(default_factory=dict)
    runs_waiting_operator: list[dict[str, Any]] = field(default_factory=list)
    runs_blocked_by_policy: list[dict[str, Any]] = field(default_factory=list)
    recent_resolution_events: list[dict[str, Any]] = field(default_factory=list)
    recent_governance_timeline_events: list[dict[str, Any]] = field(default_factory=list)
    latest_governance_event_by_run: dict[str, dict[str, Any]] = field(default_factory=dict)
    operational_governance: dict[str, Any] = field(default_factory=dict)
    governed_evolution: dict[str, Any] = field(default_factory=dict)
    latest_reasoning_trace: dict[str, Any] | None = None
    recent_reasoning_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_memory_intelligence_trace: dict[str, Any] | None = None
    recent_memory_intelligence_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_planning_intelligence_trace: dict[str, Any] | None = None
    recent_planning_intelligence_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_learning_intelligence_trace: dict[str, Any] | None = None
    recent_learning_intelligence_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_strategy_adaptation_trace: dict[str, Any] | None = None
    recent_strategy_adaptation_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_performance_optimization_trace: dict[str, Any] | None = None
    recent_performance_optimization_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_multi_agent_coordination_trace: dict[str, Any] | None = None
    recent_multi_agent_coordination_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_task_decomposition_trace: dict[str, Any] | None = None
    recent_task_decomposition_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_controlled_self_evolution_trace: dict[str, Any] | None = None
    recent_controlled_self_evolution_traces: list[dict[str, Any]] = field(default_factory=list)
    latest_self_improving_system_trace: dict[str, Any] | None = None
    recent_self_improving_system_traces: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    phase41: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        governed_evolution = dict(self.governed_evolution or {})
        return {
            "generated_at": self.generated_at,
            "goal": self.goal.as_dict() if self.goal else None,
            "goal_history": [item.as_dict() for item in self.goal_history],
            "timeline": [item.as_dict() for item in self.timeline],
            "latest_trace": self.latest_trace.as_dict() if self.latest_trace else None,
            "recent_traces": [item.as_dict() for item in self.recent_traces],
            "latest_simulation": self.latest_simulation.as_dict() if self.latest_simulation else None,
            "recent_simulations": [item.as_dict() for item in self.recent_simulations],
            "recent_episodes": [item.as_dict() for item in self.recent_episodes],
            "semantic_facts": [item.as_dict() for item in self.semantic_facts],
            "active_procedural_pattern": self.active_procedural_pattern.as_dict() if self.active_procedural_pattern else None,
            "recent_procedural_updates": [item.as_dict() for item in self.recent_procedural_updates],
            "recent_learning_signals": list(self.recent_learning_signals),
            "pending_evolution_proposal_count": self.pending_evolution_proposal_count,
            "recent_evolution_proposals": list(self.recent_evolution_proposals),
            "engine_adoption": dict(self.engine_adoption) if isinstance(self.engine_adoption, dict) else None,
            "active_runs": [dict(item) for item in self.active_runs],
            "governance_summary": dict(self.governance_summary),
            "resolution_counts": dict(self.resolution_counts),
            "runs_waiting_operator": [dict(item) for item in self.runs_waiting_operator],
            "runs_blocked_by_policy": [dict(item) for item in self.runs_blocked_by_policy],
            "recent_resolution_events": [dict(item) for item in self.recent_resolution_events],
            "recent_governance_timeline_events": [dict(item) for item in self.recent_governance_timeline_events],
            "latest_governance_event_by_run": {str(k): dict(v) for k, v in self.latest_governance_event_by_run.items()},
            "operational_governance": dict(self.operational_governance),
            "governed_evolution": governed_evolution,
            "latest_reasoning_trace": (
                dict(self.latest_reasoning_trace) if isinstance(self.latest_reasoning_trace, dict) else None
            ),
            "recent_reasoning_traces": [dict(item) for item in self.recent_reasoning_traces],
            "latest_memory_intelligence_trace": (
                dict(self.latest_memory_intelligence_trace)
                if isinstance(self.latest_memory_intelligence_trace, dict)
                else None
            ),
            "recent_memory_intelligence_traces": [dict(item) for item in self.recent_memory_intelligence_traces],
            "latest_planning_intelligence_trace": (
                dict(self.latest_planning_intelligence_trace)
                if isinstance(self.latest_planning_intelligence_trace, dict)
                else None
            ),
            "recent_planning_intelligence_traces": [dict(item) for item in self.recent_planning_intelligence_traces],
            "latest_learning_intelligence_trace": (
                dict(self.latest_learning_intelligence_trace)
                if isinstance(self.latest_learning_intelligence_trace, dict)
                else None
            ),
            "recent_learning_intelligence_traces": [dict(item) for item in self.recent_learning_intelligence_traces],
            "latest_strategy_adaptation_trace": (
                dict(self.latest_strategy_adaptation_trace)
                if isinstance(self.latest_strategy_adaptation_trace, dict)
                else None
            ),
            "recent_strategy_adaptation_traces": [dict(item) for item in self.recent_strategy_adaptation_traces],
            "latest_performance_optimization_trace": (
                dict(self.latest_performance_optimization_trace)
                if isinstance(self.latest_performance_optimization_trace, dict)
                else None
            ),
            "recent_performance_optimization_traces": [dict(item) for item in self.recent_performance_optimization_traces],
            "latest_multi_agent_coordination_trace": (
                dict(self.latest_multi_agent_coordination_trace)
                if isinstance(self.latest_multi_agent_coordination_trace, dict)
                else None
            ),
            "recent_multi_agent_coordination_traces": [dict(item) for item in self.recent_multi_agent_coordination_traces],
            "latest_task_decomposition_trace": (
                dict(self.latest_task_decomposition_trace)
                if isinstance(self.latest_task_decomposition_trace, dict)
                else None
            ),
            "recent_task_decomposition_traces": [dict(item) for item in self.recent_task_decomposition_traces],
            "latest_controlled_self_evolution_trace": (
                dict(self.latest_controlled_self_evolution_trace)
                if isinstance(self.latest_controlled_self_evolution_trace, dict)
                else None
            ),
            "recent_controlled_self_evolution_traces": [dict(item) for item in self.recent_controlled_self_evolution_traces],
            "latest_self_improving_system_trace": (
                dict(self.latest_self_improving_system_trace)
                if isinstance(self.latest_self_improving_system_trace, dict)
                else None
            ),
            "recent_self_improving_system_traces": [dict(item) for item in self.recent_self_improving_system_traces],
            "warnings": list(self.warnings),
            "phase41": dict(self.phase41) if isinstance(self.phase41, dict) else {},
        }

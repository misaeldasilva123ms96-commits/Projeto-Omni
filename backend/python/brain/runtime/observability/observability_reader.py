from __future__ import annotations

from pathlib import Path

from brain.runtime.control.governance_taxonomy import GovernanceReason
from brain.runtime.evolution.evolution_program_closure import normalize_governed_evolution_summary

from .engine_adoption_reader import read_engine_adoption
from .goal_reader import GoalReader
from .memory_reader import MemoryReader
from .models import GoalSnapshot, ObservabilitySnapshot, TraceSnapshot, utc_now_iso
from .run_reader import (
    read_active_runs,
    read_evolution_summary,
    read_latest_learning_intelligence_trace,
    read_latest_memory_intelligence_trace,
    read_latest_planning_intelligence_trace,
    read_latest_reasoning_trace,
    read_latest_governance_event_by_run,
    read_operational_governance,
    read_recent_learning_intelligence_traces,
    read_recent_memory_intelligence_traces,
    read_recent_planning_intelligence_traces,
    read_recent_reasoning_traces,
    read_recent_governance_timeline_events,
    read_recent_resolution_events,
    read_resolution_summary,
    read_runs_waiting_operator,
)
from .simulation_reader import SimulationReader
from .specialist_reader import SpecialistReader
from .timeline_reader import TimelineReader


class ObservabilityReader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.goal_reader = GoalReader(root)
        self.timeline_reader = TimelineReader(root)
        self.specialist_reader = SpecialistReader(root)
        self.simulation_reader = SimulationReader(root)
        self.memory_reader = MemoryReader(root)

    def snapshot(self) -> ObservabilitySnapshot:
        state = self.timeline_reader.read_state()
        progress_score = state.current_progress if state else None
        goal = self.goal_reader.read_active_goal(progress_score=progress_score)
        latest_trace = self.specialist_reader.read_latest_trace()
        if goal and latest_trace:
            self._enrich_goal_from_trace(goal, latest_trace)

        goal_type = self._goal_type(goal)
        semantic_subject = goal_type or (goal.intent if goal else None)
        latest_simulation = self.simulation_reader.read_latest_simulation(goal_id=goal.goal_id if goal else None)
        pending_count, recent_proposals = self.memory_reader.read_pending_evolution_proposals(limit=6)
        governance_summary = read_resolution_summary(self.root)
        waiting_operator = read_runs_waiting_operator(self.root)
        recent_resolution_events = read_recent_resolution_events(self.root, limit=25)
        recent_governance_timeline_events = read_recent_governance_timeline_events(self.root, limit=25)
        latest_governance_event_by_run = read_latest_governance_event_by_run(self.root)
        operational_governance = read_operational_governance(self.root, timeline_limit=25)
        governed_evolution = normalize_governed_evolution_summary(read_evolution_summary(self.root, recent_limit=10))
        latest_reasoning_trace = read_latest_reasoning_trace(self.root)
        recent_reasoning_traces = read_recent_reasoning_traces(self.root, limit=10)
        latest_memory_intelligence_trace = read_latest_memory_intelligence_trace(self.root)
        recent_memory_intelligence_traces = read_recent_memory_intelligence_traces(self.root, limit=10)
        latest_planning_intelligence_trace = read_latest_planning_intelligence_trace(self.root)
        recent_planning_intelligence_traces = read_recent_planning_intelligence_traces(self.root, limit=10)
        latest_learning_intelligence_trace = read_latest_learning_intelligence_trace(self.root)
        recent_learning_intelligence_traces = read_recent_learning_intelligence_traces(self.root, limit=10)
        policy = GovernanceReason.POLICY_BLOCK.value

        def _is_policy_block(item: dict) -> bool:
            if str(item.get("reason", "")).strip() == policy:
                return True
            gov = item.get("governance")
            if isinstance(gov, dict) and str(gov.get("reason", "")).strip() == policy:
                return True
            return False

        blocked_by_policy = [item for item in recent_resolution_events if _is_policy_block(item)]

        return ObservabilitySnapshot(
            generated_at=utc_now_iso(),
            goal=goal,
            goal_history=self.goal_reader.read_goal_history(limit=6),
            timeline=self.timeline_reader.read_recent_events(limit=25),
            latest_trace=latest_trace,
            recent_traces=self.specialist_reader.read_recent_traces(limit=6),
            latest_simulation=latest_simulation,
            recent_simulations=self.simulation_reader.read_recent_simulations(limit=6, goal_id=goal.goal_id if goal else None),
            recent_episodes=self.memory_reader.read_recent_episodes(goal_id=goal.goal_id if goal else None, limit=8),
            semantic_facts=self.memory_reader.read_top_semantic_facts(subject=semantic_subject, limit=8),
            active_procedural_pattern=self.memory_reader.read_active_procedural_pattern(goal_type),
            recent_procedural_updates=self.memory_reader.read_recent_procedural_updates(limit=5),
            recent_learning_signals=self.memory_reader.read_recent_learning_signals(limit=8),
            pending_evolution_proposal_count=pending_count,
            recent_evolution_proposals=recent_proposals,
            engine_adoption=read_engine_adoption(self.root),
            active_runs=read_active_runs(self.root),
            governance_summary=governance_summary,
            resolution_counts=dict(governance_summary.get("resolution_counts", {}) or {}),
            runs_waiting_operator=waiting_operator,
            runs_blocked_by_policy=blocked_by_policy[:25],
            recent_resolution_events=recent_resolution_events,
            recent_governance_timeline_events=recent_governance_timeline_events,
            latest_governance_event_by_run=latest_governance_event_by_run,
            operational_governance=operational_governance,
            governed_evolution=governed_evolution,
            latest_reasoning_trace=latest_reasoning_trace,
            recent_reasoning_traces=recent_reasoning_traces,
            latest_memory_intelligence_trace=latest_memory_intelligence_trace,
            recent_memory_intelligence_traces=recent_memory_intelligence_traces,
            latest_planning_intelligence_trace=latest_planning_intelligence_trace,
            recent_planning_intelligence_traces=recent_planning_intelligence_traces,
            latest_learning_intelligence_trace=latest_learning_intelligence_trace,
            recent_learning_intelligence_traces=recent_learning_intelligence_traces,
            warnings=[],
        )

    def goal_history(self, *, limit: int = 10) -> list[dict[str, object]]:
        return [item.as_dict() for item in self.goal_reader.read_goal_history(limit=limit)]

    def trace_history(self, *, limit: int = 10) -> list[dict[str, object]]:
        return [item.as_dict() for item in self.specialist_reader.read_recent_traces(limit=limit)]

    def simulation_history(self, *, limit: int = 10, goal_id: str | None = None) -> list[dict[str, object]]:
        return [item.as_dict() for item in self.simulation_reader.read_recent_simulations(limit=limit, goal_id=goal_id)]

    @staticmethod
    def _goal_type(goal: GoalSnapshot | None) -> str | None:
        if goal is None:
            return None
        metadata_goal_type = goal.metadata.get("goal_type") if isinstance(goal.metadata, dict) else None
        if isinstance(metadata_goal_type, str) and metadata_goal_type.strip():
            return metadata_goal_type.strip()
        if goal.intent.strip():
            return goal.intent.strip()
        return None

    @staticmethod
    def _enrich_goal_from_trace(goal: GoalSnapshot, trace: TraceSnapshot) -> None:
        validator = None
        for decision in reversed(trace.decisions):
            if decision.specialist_type == "validator":
                validator = decision
                break
        if validator is None:
            return
        criteria_met = set(str(item) for item in validator.metadata.get("criteria_met", []) if str(item).strip())
        criteria_failed = set(str(item) for item in validator.metadata.get("criteria_failed", []) if str(item).strip())
        criteria_pending = set(str(item) for item in validator.metadata.get("criteria_pending", []) if str(item).strip())
        for criterion in goal.success_criteria:
            if criterion.description in criteria_met:
                criterion.status = "met"
            elif criterion.description in criteria_failed:
                criterion.status = "failed"
            elif criterion.description in criteria_pending:
                criterion.status = "pending"
        progress_score = validator.metadata.get("progress_score")
        if isinstance(progress_score, (int, float)):
            goal.progress_score = max(0.0, min(1.0, float(progress_score)))


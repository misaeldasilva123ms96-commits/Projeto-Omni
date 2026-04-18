# Phase 24 - Cognitive Specialist Architecture

## Mission

Phase 24 introduces a governed specialist layer inside the Omni runtime. The goal is to make internal cognitive roles explicit without turning the runtime into an uncontrolled multi-agent system.

## Specialist Philosophy

Specialists are bounded internal roles, not autonomous agents. They do not negotiate directly, do not spawn their own loops, and do not bypass goal constraints, simulation safety, continuation boundaries, or governance policy.

The coordinator is the only arbiter.

## Specialist Roles

- `PlannerSpecialist`
  - Produces bounded planning or replan decisions.
  - Prefers explicit goal type metadata when available.
- `ExecutorSpecialist`
  - Wraps the existing execution path.
  - Never creates a second execution engine.
- `ValidatorSpecialist`
  - Validates results against goal criteria.
  - Distinguishes `criteria_met`, `criteria_failed`, and `criteria_pending`.
- `RepairSpecialist`
  - Produces bounded repair advice.
  - Uses repair history and simulation hints conservatively.
- `GovernanceSpecialist`
  - Has real veto power.
  - Can `approve`, `hold`, or `block`.
- `SynthesisSpecialist`
  - Produces a final structured summary of the specialist path.

## Coordinator Role

`SpecialistCoordinator` is the only sequencing path for specialists.

It is responsible for:

1. creating a coordination trace
2. invoking planner
3. invoking governance review at planning and execution boundaries
4. invoking executor through the existing runtime execution path
5. invoking validator
6. invoking bounded repair advice when needed
7. invoking synthesis
8. persisting the coordination trace

## Governance Model

Governance is intentionally conservative.

- clear hard-constraint violations can block immediately
- medium-risk actions can be held when constraint context is incomplete
- low-risk bounded actions may approve

If constraint registry context is absent or partial, governance does not fail open for moderate or high risk actions.

## Trace Model

The coordination trace is the primary audit artifact of this phase.

It persists:

- specialist decisions
- governance verdicts
- final outcome
- session and goal linkage

Storage path:

- `.logs/fusion-runtime/specialists/coordination_log.jsonl`

The store is append-only and non-blocking on persistence failure.

## Executor Wrapper Requirement

`ExecutorSpecialist` delegates to the existing execution callback supplied by the runtime orchestrator. This preserves trusted execution, self-repair, learning ingestion, orchestration, and evolution hooks that already exist in the core execution path.

This phase does not add a parallel executor.

## Pending Evaluative Criteria

Evaluative success criteria are not treated as immediate failures when broader synthesis or later review is still required.

The validator surfaces them as:

- `criteria_pending`

This keeps goal-oriented validation compatible with future deeper evaluation phases.

## Integration Points

- `orchestrator.py`
  - initializes `SpecialistCoordinator`
  - uses it additively for active-goal execution flows
- `continuation_decider.py`
  - accepts optional `coordination_trace`
- `continuation_executor.py`
  - propagates optional coordination trace metadata
- `memory_facade.py`
  - `close_goal_episode(...)` now accepts optional `coordination_trace_id`

## Coordination Safety

Coordination locking is session-scoped, not global. This prevents cross-session contention while still guarding trace construction and bounded sequencing inside a single runtime session.

## Limitations

- specialists remain intra-runtime roles, not independent agents
- repair remains advisory in this phase
- coordinator integration is intentionally additive rather than a full runtime rewrite
- validator pending semantics are conservative and intentionally simple for evaluative criteria

## How This Prepares Phase 25

Phase 24 establishes explicit cognitive roles, audit traces, and governance-aware coordination. That gives Phase 25 a safe foundation for richer internal composition or observability without abandoning the bounded control model already established across Phases 14-24.

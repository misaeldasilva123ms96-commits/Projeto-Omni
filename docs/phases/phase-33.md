# Phase 33 — Planning Intelligence System

Phase 33 adds a **bounded planning intelligence layer** between Phase 31 reasoning and runtime execution. It turns the reasoning handoff into a **dependency-aware, checkpointed execution plan** that is auditable and consumable by the orchestrator path.

## Implemented Scope

- **`PlanningEngine`** (`brain/runtime/planning/planning_engine.py`): deterministic synthesis of an `ExecutionPlan` from:
  - reasoning `execution_handoff` (`plan_steps`, task metadata, suggested capabilities),
  - `ReasoningTrace` identifiers (`trace_id`),
  - optional **control routing** hints (risk / verification intensity) after the control layer allows execution.
- **Structured models** (`brain/runtime/planning/intelligence_models.py`):
  - `ExecutionPlan` — plan identity, session/run/task linkage, readiness flag, steps, checkpoints, fallbacks, reasoning linkage.
  - `ExecutionPlanStep` — id, type, summary, description, `depends_on`, validation linkage, optional fallback edge id, capability hints.
  - `PlanCheckpointBinding` — checkpoint id, label, `after_step_id`, `validation_kind`.
  - `PlanFallbackEdge` — trigger step, optional target step, notes.
  - `PlanningTrace` — compact observability (counts, readiness, degraded flag, error text).
- **Runtime integration** (`BrainOrchestrator.run`):
  - After **control approves** execution (`runtime.control.execution_allowed`), the engine builds the plan and appends **`runtime.planning_intelligence.trace`** to `execution-audit.jsonl`.
  - Swarm / Node `context_session` receives `execution_plan` and `planning_trace` when execution continues to the swarm path.
  - Session persistence includes `planning_intelligence` alongside reasoning and memory intelligence payloads.
- **Safe degradation**: internal synthesis errors yield a **single-step degraded plan** with mandatory checkpoint (`PlanningTrace.degraded=True`); the orchestrator path continues.
- **Observability**: `read_recent_planning_intelligence_traces` / `read_latest_planning_intelligence_trace` and `ObservabilitySnapshot` fields mirror Phase 31/32 trace patterns.

## What This Phase Does *Not* Include (by design)

- **Phase 34 — Runtime learning**: no policy or plan mutation from outcomes.
- **Phase 35+ strategy adaptation / multi-agent autonomy / self-evolution**: not started.
- **Operational `TaskPlan` lifecycle** (`PlanningExecutor`, resumable workflows): unchanged; Phase 33 plans are a **parallel, reasoning-grounded execution contract** for the chat path, not a replacement for goal-bound task plans.
- **Full DAG scheduler**: dependencies are validated (acyclic, resolvable) but there is no general parallel scheduler.

## Flow (integrated path)

```text
OIL + memory context → ReasoningEngine → control layer → PlanningEngine → execution (swarm / session)
```

Reasoning remains authoritative for proceed / block; planning refines **allowed** work into structured steps. Memory continues to influence reasoning only (indirectly).

## Verification

Run Python tests under `tests/runtime/planning/` and regression tests for reasoning, memory, observability, and orchestrator integration.

# Phase 38 — Autonomous Task Decomposition

## Scope (implemented)

Phase 38 adds **bounded, auditable subtask generation** after **Planning (33)** and before **Multi-agent coordination (37)** on the main `BrainOrchestrator.run` path.

- **`TaskDecomposer`** (`brain.runtime.decomposition.task_decomposer.py`): reads `ExecutionPlan` steps plus **reasoning trace** and **strategy** summaries; emits **`SubTask`** records (`analysis`, `generation`, `validation`, `execution`) with explicit `parent_step_id`, `depends_on`, and `depth`.
- **Hard limits** (`decomposition_limits.py`): `MAX_SUBTASKS = 6`, `MAX_DEPTH = 2`, `MAX_BRANCHES_PER_NODE = 3`. Decomposition stops when limits hit; **`truncated`** / warnings on the trace.
- **Planning payload**: `planning_payload["task_decomposition"]` holds `{ subtasks, trace }`; **`execution_plan["subtasks"]`** is enriched for downstream consumers (coordination, swarm slimming).
- **Coordination**: `CoordinationState` carries decomposition counts/truncation; planner/executor/validator/critic use **`task_decomposition`** (validator runs **`validate_subtask_dependencies`**); handoff bundle includes **`task_decomposition_ref`**.
- **Observability**: `runtime.task_decomposition.trace` with `trace`, capped `subtasks`, `degraded`/`error` on failure. Readers: `read_recent_task_decomposition_traces` / `read_latest_task_decomposition_trace`; snapshot fields on `ObservabilitySnapshot`.
- **Performance (36)**: `compress_execution_plan` includes a capped **`subtasks`** slice for the swarm boundary.

## Governance

Subtasks **do not execute independently**; they are structured annotations. Control-plane allow/block is unchanged. Coordination remains advisory relative to governance.

## Phase 39+ (not implemented)

- Self-evolution, unbounded agent spawning, distributed DAG schedulers, learned decomposition policies — **out of scope**.

## Tests

`tests/runtime/decomposition/test_task_decomposer.py` covers linkage, truncation, per-node branch cap, and depth cap.

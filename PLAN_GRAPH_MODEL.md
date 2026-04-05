# Plan Graph Model

## Goal

The plan graph extends the runtime beyond a flat step list when task structure benefits from dependency awareness or safe parallel scheduling.

## Structure

Implementation:

- `core/planning/planGraph.js`
- emitted by `features/multiagent/specialists/advancedPlannerSpecialist.js`

Graph fields:

- `version`
- `mode`
- `nodes`

Node fields:

- `node_id`
- `step_id`
- `selected_tool`
- `selected_agent`
- `tool_arguments`
- `goal`
- `depends_on`
- `parallel_safe`
- `retryable`
- `state`

## Fallback To Linear Plans

The planner emits:

- `plan_kind = linear` for simple tasks
- `plan_kind = graph` when dependencies or safe parallelism are useful

## Node Lifecycle

Graph nodes progress through:

- `pending`
- `completed`
- `failed`

## Dependency Handling

- nodes become ready only when `depends_on` nodes are completed
- ready read-only nodes can be grouped into bounded parallel batches
- blocked graphs stop instead of guessing through missing dependencies

## Checkpoint And Resume Integration

- `plan_graph` is persisted into checkpoints
- `plan_signature` is persisted and validated on resume
- stale or incompatible graph checkpoints are rejected before execution continues

## Observability

Graph execution is visible through:

- `runtime.graph.plan`
- `runtime.parallel.start`
- step-level audit rows with `plan_kind`

## Scope Boundary

This is a bounded execution graph for runtime planning, not a general-purpose workflow engine.

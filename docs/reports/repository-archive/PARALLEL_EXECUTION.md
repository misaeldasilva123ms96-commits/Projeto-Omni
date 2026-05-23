# Parallel Execution

## Scope

Phase 5 introduces controlled parallelism only for safe read-only work.

## Allowed Parallel Task Types

Currently allowed:

- `glob_search`
- `grep_search`
- explicit `read_file` actions in a graph when marked `parallel_safe`

Currently not allowed:

- `write_file`
- permission-sensitive destructive work
- unbounded parallel fan-out

## Concurrency Limits

Primary control:

- `OMINI_MAX_PARALLEL_READ_STEPS`

Default live value:

- `2`

## Merge Strategy

1. ready nodes are grouped into a bounded batch
2. each read-only action runs independently
3. normalized results are merged back into orchestrator order

## Safety Boundaries

- only read-only work is eligible
- permissions still apply to every action
- dependency order is enforced before scheduling
- sequential fallback remains available when graph or safety checks do not justify parallelism

## Observability

Parallel execution emits:

- `runtime.parallel.start`
- step-level transcript and audit records

## Fallback

If the graph is not safe for parallelism, the same plan executes sequentially.

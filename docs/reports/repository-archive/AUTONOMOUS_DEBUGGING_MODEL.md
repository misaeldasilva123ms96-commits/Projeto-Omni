# Autonomous Debugging Model

## Goal

The debug loop provides a bounded repair path for engineering tasks that fail tests.

## Live loop

`DebugLoopController.run(...)` performs:

1. run tests
2. inspect failure output
3. propose a patch candidate
4. review patch risk
5. apply the patch
6. rerun tests
7. rollback if verification still fails
8. stop after `max_iterations`

## Persisted outputs

- `patch_history`
- `debug_iterations`
- `test_results`
- `workspace_state`

## Strategy interaction

This loop is designed to feed future strategy memory updates through explicit success/failure outcomes.

## Boundaries

- the repair heuristic is intentionally narrow in Phase 9
- the loop is bounded by iteration count and existing runtime supervision

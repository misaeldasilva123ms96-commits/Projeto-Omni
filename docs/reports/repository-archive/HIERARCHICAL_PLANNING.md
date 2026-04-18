# Hierarchical Planning

## Model
- Root goal: one top-level objective for the task.
- Subgoals: bounded grouped execution intents such as inspect, read, synthesize.
- Steps: executable actions already supported by the live runtime.

## Execution flow
1. The Node planner detects when a request warrants hierarchy.
2. It assigns `goal_id` and `parent_goal_id` to steps.
3. It emits both `plan_graph` and `plan_hierarchy`.
4. The Python runtime executes the steps through the existing bounded execution loop.
5. Checkpoints, audit logs, and run summaries retain the hierarchy metadata.

## Checkpoint and resume
- `plan_hierarchy` is persisted in checkpoints.
- Resume reuses the remaining action list plus the stored hierarchy context.

## Compatibility
- Linear plans remain supported.
- Graph plans remain supported.
- Hierarchical mode is only selected when the request structure justifies it.

## Observability
- `runtime.goal.plan`
- goal IDs on step transcript and audit events
- hierarchy summary in `run-summaries.jsonl`

# Milestone Management Model

## Live implementation

`milestone_manager.py` owns milestone runtime state updates.

## State fields

- `milestone_id`
- `title`
- `state`
- `step_ids`
- `blockers`
- `progress`

Aggregate fields:

- `completed_milestones`
- `blocked_milestones`

## Update rule

Milestones are updated from executed step results and action-linked `milestone_id` values.

## Inspection

Milestone plan and state are exposed through checkpoints, run summaries, execution state, and `inspect_milestones`.

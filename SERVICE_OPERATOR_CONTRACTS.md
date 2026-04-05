# Service Operator Contracts

## Complex task submission
- `execute_task(user_id, session_id, message)`

## Inspection contracts
- `inspect_run(run_id)`
- `inspect_plan_hierarchy(run_id)`
- `inspect_reflection(run_id)`
- `inspect_learning_memory()`
- `inspect_branches(run_id)`
- `inspect_contributions(run_id)`
- `inspect_simulation(run_id)`
- `inspect_run_intelligence(run_id)`

## Coordination data exposed
- hierarchy
- branch state
- cooperative plan
- simulation summary
- strategy suggestions
- run intelligence summary

## Operator-safe model
- inspection is read-only
- contracts expose structured coordination data instead of raw hidden runtime internals
- ready for future API/dashboard wrapping without changing execution authority

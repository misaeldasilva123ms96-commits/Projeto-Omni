# Cognitive Telemetry

## Event taxonomy
- `runtime.goal.plan`
- `runtime.graph.plan`
- `runtime.parallel.start`
- `runtime.reflection`
- `runtime.learning_memory.updated`
- `runtime.step`
- `runtime.step.audit`
- `runtime.run.summary`

## Correlation
All telemetry is correlated by:
- session_id
- task_id
- run_id
- step_id
- goal_id where available

## Run summary schema
Stored in `.logs/fusion-runtime/run-summaries.jsonl`.
Fields include:
- plan kind
- hierarchy
- reflection summary
- status
- step summaries with goal lineage

## UI readiness
This phase does not build a dashboard, but it produces machine-readable summaries and event streams that make a dashboard straightforward later.

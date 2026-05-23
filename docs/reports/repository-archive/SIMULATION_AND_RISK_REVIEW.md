# Simulation And Risk Review

## Triggering
- risky write requests
- critic-requested revisions
- branch-worthy comparison tasks
- explicit compare/simulate phrasing

## Output
- risk score
- blockers
- alternative suggestions
- recommended decision: proceed, revise, or stop

## Runtime effect
- simulation runs before execution
- `recommended_decision = stop` blocks execution in the live Python loop
- simulation summaries are stored in checkpoints and run summaries

## Observability
- event: `runtime.simulation.review`
- inspection path: `inspect_simulation(run_id)`

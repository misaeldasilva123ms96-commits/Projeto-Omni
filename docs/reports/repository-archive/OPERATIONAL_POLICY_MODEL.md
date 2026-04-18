# Operational Policy Model

## Policy levels
- low
- medium
- high

## Blocker taxonomy
- missing_approval
- unsafe_parallel_mutation
- specialist_scope_violation
- stale_checkpoint
- permission_denied
- policy_stop

## Operator-facing behavior
- Stop reasons are surfaced in runtime outputs and status inspection.
- Policy decisions are machine-readable and logged.
- Mutating steps without approval are blocked before execution.

## Synthesis behavior
- The runtime favors clear blocker messaging over silent failure.
- Reflection can convert policy outcomes into future failure-avoidance lessons.

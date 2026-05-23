# Advanced Simulation Model

## Outputs
- `risk_score`
- `confidence_estimate`
- `estimated_cost`
- `policy_flags`
- `recommended_decision`
- `recommended_path`

## What is simulated
- policy blockers
- branch safety
- likely path cost
- critic-requested revision pressure

## Runtime effect
- simulation can proceed
- simulation can revise
- simulation can stop execution before tools run

## Boundaries
- simulation is optional through runtime config
- simulation is not a hidden planner replacement

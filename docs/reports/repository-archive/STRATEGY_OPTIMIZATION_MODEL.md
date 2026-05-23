# Strategy Optimization Model

## Inputs
- ranked strategy memory
- current task message
- planner output

## Outputs
- selected strategy
- preferred plan mode
- step biases
- optimization summary

## Influence
- plan mode preference can move toward tree execution
- read-only-first strategies can bias ordering
- branch-friendly strategies can bias comparison paths

## Guardrails
- optimization is explainable
- no black-box reinforcement learning
- provenance remains visible through ranked strategy records

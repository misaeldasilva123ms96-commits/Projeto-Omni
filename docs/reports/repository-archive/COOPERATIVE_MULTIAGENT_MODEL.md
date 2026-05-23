# Cooperative Multi-Agent Model

## Shared-goal coordination
- one `shared_goal_id` binds multiple specialist contributions to the same task outcome
- planner, researcher, reviewer, critic, and synthesizer can all contribute under orchestrator control

## Contribution lifecycle
- planned
- active
- completed
- pruned
- failed

## Dependency-aware cooperation
- planner contributes first
- researcher/reviewer depend on planner output
- critic can gate risky plans
- synthesizer fuses after upstream evidence exists

## Authority
- the orchestrator remains the only final decision-maker
- specialists never become independent planning authorities

## Telemetry
- contributions carry `specialist_id`, `role`, `shared_goal_id`, `depends_on`, confidence, and optional `branch_id`

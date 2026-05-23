# Critic Model

## Role

The critic is a bounded quality-control specialist, not a second brain.

Active implementation:

- `features/multiagent/specialists/criticSpecialist.js`
- live integration through:
  - `core/brain/queryEngineAuthority.js`
  - `backend/python/brain/runtime/orchestrator.py`

## Invocation Conditions

The critic is conditional:

- plan review when risk is above threshold
- outcome review when execution is weak or failing
- disabled entirely if `OMINI_ENABLE_CRITIC=false`

## Decision Outputs

The critic can recommend:

- `approve`
- `revise`
- `retry`
- `stop`

## Relationship To Planner And Evaluator

- planner proposes execution structure
- evaluator classifies step success/failure
- critic inspects risky plans and suspicious outcomes
- master orchestrator still owns execution flow and final synthesis

## Audit And Logging

The runtime emits critic-aware records through:

- `runtime.critic.plan`
- step evaluations with embedded `critic` review
- correction events in transcript/audit entries

## Stop And Escalation Rules

- repeated weak read-only outcomes can trigger bounded `retry`
- risky but incomplete plans can trigger `revise`
- permission-sensitive or suspicious states can trigger `stop`
- the orchestrator remains responsible for whether to continue or surface the blocker

## Boundary

The critic does not execute tools, does not own the final answer, and does not replace the planner or evaluator.

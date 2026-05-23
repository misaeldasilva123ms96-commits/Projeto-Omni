# Cognitive Control Model

## Planner

Owner:

- [`features/multiagent/specialists/plannerSpecialist.js`](./features/multiagent/specialists/plannerSpecialist.js)

Responsibilities:

- decompose tasks
- extract constraints
- order steps
- identify dependencies and execution bounds

## Evaluator

Owner:

- [`features/multiagent/specialists/evaluatorSpecialist.js`](./features/multiagent/specialists/evaluatorSpecialist.js)
- live orchestration application in [`backend/python/brain/runtime/orchestrator.py`](./backend/python/brain/runtime/orchestrator.py)

Responsibilities:

- inspect step outcomes
- classify blockers
- choose:
  - `continue`
  - `retry_same_step`
  - `revise_plan`
  - `stop_blocked`
  - `stop_failed`

## Synthesizer

Owner:

- [`features/multiagent/specialists/synthesizerSpecialist.js`](./features/multiagent/specialists/synthesizerSpecialist.js)

Responsibilities:

- turn raw step history into grounded final responses
- prefer read-result content for direct artifact requests
- preserve failure context when the task only partially completes

## Orchestration Relationship

- master orchestrator remains the only final authority
- planner proposes
- evaluator governs progression
- synthesizer shapes the final answer

None of these roles form a second brain.

## Correction Decision Logic

- permission denial -> stop immediately
- path-not-found -> bounded plan revision when a semantic or previous artifact candidate exists
- transient failure -> bounded retry
- repeated failure -> stop and surface blocker

## Stop Conditions

- permission blocked
- retry budget exhausted
- max-step budget exhausted
- no meaningful path revision available

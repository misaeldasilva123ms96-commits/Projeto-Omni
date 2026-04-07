# Large Task Decomposition Model

## Model

Large requests are decomposed into:

- root engineering goal
- epics
- milestones
- implementation and verification steps

## Inputs

- repository analysis
- repo impact analysis
- verification plan
- user request text

## Live flow

`advancedPlannerSpecialist` detects large-project engineering requests and calls `buildLargeTaskPlan`, which returns:

- `milestone_tree`
- `epics`
- `module_candidates`
- `integration_risk_summary`

The same planner then emits milestone-linked execution steps that feed the execution tree.

## Checkpointability

Milestone plan and milestone state are persisted inside `engineering_data` in checkpoints and run summaries.

## Operator visibility

Milestone data is available through:

- task status
- run summaries
- `inspect_milestones`
- execution state payloads

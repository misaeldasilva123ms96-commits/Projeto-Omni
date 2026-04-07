# Large Task Run Intelligence

## Run summary additions

Phase 10 run summaries now include engineering state with:

- repository analysis
- repo impact analysis
- impact map
- milestone plan
- milestone state
- patch history
- patch sets
- verification plan
- verification selection
- verification summary
- PR summary
- merge readiness

## Execution state additions

Execution state now exposes:

- `milestone_tree`
- `impact_map`
- `patch_sets`
- `verification_status`
- `integration_status`
- `merge_readiness`
- `unresolved_blockers`
- `pr_summary`

## Operator inspections

Task service now supports:

- `inspect_milestones`
- `inspect_patch_sets`
- `inspect_verification`
- `inspect_pr_summary`

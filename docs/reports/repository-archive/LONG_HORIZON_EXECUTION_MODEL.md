# Long Horizon Execution Model

## Runtime tracking

Phase 10 extends run tracking with:

- `task_id`
- `run_id`
- milestone plan and milestone state
- patch sets
- verification summary
- PR-style summary

## Persistence

Long-horizon engineering state is stored in checkpoint `engineering_data` and mirrored into run summaries.

## Resume

Resume continues through the existing checkpoint engine while restoring:

- repository analysis
- repo impact analysis
- verification plan
- verification selection
- milestone plan
- engineering workflow metadata

## Boundary

Resume remains run-level rather than milestone-scheduler-level.

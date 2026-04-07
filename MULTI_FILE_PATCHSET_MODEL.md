# Multi File Patchset Model

## Patch set object

Patch sets include:

- `patch_set_id`
- `affected_files`
- `dependency_notes`
- `risk_level`
- `verification_plan`
- `patches`

## Live implementation

`patch_set_manager.py` provides:

- build
- review
- apply
- rollback
- summary

## Safety

- patch sets are reversible
- review runs before apply
- partial apply triggers rollback
- state remains auditable in engineering runtime data

## Current boundary

The patch-set engine is live and tested, but the default large-project live path still favors planning, inspection, and verification before broad mutation.

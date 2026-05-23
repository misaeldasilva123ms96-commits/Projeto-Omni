# Engineering Run Intelligence

## New machine-readable engineering data

Phase 9 extends runtime intelligence with:
- `repository_analysis`
- `workspace_state`
- `patch_history`
- `debug_iterations`
- `test_results`
- `engineering_review`
- `engineering_workflow`

## Where it appears

- checkpoints
- execution state payloads
- run summaries
- task status envelopes
- task service inspection endpoints

## Operator inspection

`TaskService` now supports:
- repository analysis inspection
- patch history inspection
- debug iteration inspection
- workspace state inspection

## Purpose

This data is intended for:
- future developer/operator dashboards
- long-run engineering inspection
- debugging autonomous code modification behavior

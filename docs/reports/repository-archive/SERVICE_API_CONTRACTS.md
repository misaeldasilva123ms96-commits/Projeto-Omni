# Service API Contracts

## Goal

Phase 5 makes the runtime easier to expose through an API by separating internal orchestration details from service-facing task envelopes.

## Active Contract Layer

Implementation:

- `backend/python/brain/runtime/service_contracts.py`
- `backend/python/brain/runtime/task_service.py`

## Start Task Contract

Validated input:

- `user_id`
- `session_id`
- `message`

Normalized output envelope:

- `status`
- `user_id`
- `session_id`
- `task_id`
- `response`
- `links`

## Task Status Contract

`TaskService.task_status(run_id=...)` returns:

- `run_id`
- `task_id`
- `session_id`
- `status`
- `next_step_index`
- `total_actions`

## Resume Task Contract

`TaskService.resume_task(run_id=...)` returns:

- `status`
- `response`
- `run_id`
- `task_id`
- `step_results`
- optional `error`

## Transcript And Audit References

Primary references:

- transcript: `.logs/fusion-runtime/runtime-transcript.jsonl`
- audit: `.logs/fusion-runtime/execution-audit.jsonl`
- checkpoints: `.logs/fusion-runtime/checkpoints/*.json`

## Identity Model

The service-facing boundary distinguishes:

- `user_id`
- `session_id`
- `task_id`
- `run_id`
- `step_id`

## Multi-User And Session Isolation

- execution requests are session-scoped
- memory retrieval remains session-aware
- checkpoints are run-scoped
- task identity remains separate from session identity

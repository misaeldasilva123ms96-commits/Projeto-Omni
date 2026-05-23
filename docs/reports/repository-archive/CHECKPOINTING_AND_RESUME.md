# Checkpointing And Resume

## Checkpoint Format

Store:

- `.logs/fusion-runtime/checkpoints/<run_id>.json`

Payload includes:

- `run_id`
- `task_id`
- `session_id`
- `message`
- `status`
- `next_step_index`
- `completed_steps`
- `remaining_actions`
- `total_actions`
- `updated_at`

## What State Is Persisted

- run identity
- task identity
- session identity
- executed step outcomes
- next actionable index
- remaining action payloads for resume

## How Resume Works

1. load checkpoint by `run_id`
2. read `remaining_actions`
3. execute the remaining actions through the same live runtime loop
4. produce a resumed grounded response

Current implementation:

- [`backend/python/brain/runtime/checkpoint_store.py`](./backend/python/brain/runtime/checkpoint_store.py)
- `BrainOrchestrator.resume_run(...)`

## Failure Recovery Boundaries

- resume is bounded to stored remaining actions
- no speculative re-planning on resume yet
- if remaining actions are empty, resume returns a completed/no-op status

## Limitations

- checkpointing is local-file based
- no distributed locking
- no long-lived worker queue yet

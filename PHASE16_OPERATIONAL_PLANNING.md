# Phase 16 - Operational Planning Layer

## Mission

Phase 16 introduces the first durable continuity layer for Omni. The goal is to make multi-step runtime work explicit, stateful, resumable, and auditable across execution turns without replacing the existing trusted execution or controlled self-repair layers.

## Planning Philosophy

Operational planning in this phase is deterministic and compact:

1. only plannable work receives a persisted operational plan
2. plans represent concrete runtime work, not speculative essays
3. step state transitions are explicit and typed
4. checkpoints are written at meaningful operational boundaries
5. resume is conservative and fails safely on inconsistent state
6. summaries are persisted so the next turn can recover continuity quickly

## Architecture

The planning layer lives in `backend/python/brain/runtime/planning/` and is composed of:

- `models.py`
  - typed plan, step, checkpoint, summary, classification, and resume models
- `task_classifier.py`
  - deterministic task classification rules
- `plan_builder.py`
  - explicit operational plan construction
- `task_state_store.py`
  - JSON persistence for plans, checkpoints, and summaries
- `checkpoint_manager.py`
  - compact checkpoint creation
- `progress_tracker.py`
  - explicit step lifecycle updates and progress computation
- `resume_engine.py`
  - deterministic resume decisions
- `operational_summary.py`
  - next-turn continuity summaries
- `planning_executor.py`
  - orchestration layer for plan creation, updates, checkpoints, resume, and summaries

## Task Classification Model

The classifier returns one of:

- `single_step`
- `multi_step`
- `resumable_workflow`
- `long_running_work`
- `non_plannable`

Current deterministic triggers:

- no actions -> `non_plannable`
- one short safe read action -> `single_step`
- multiple actions or mutating/validation tools -> `multi_step`
- retries, workflow signals, or resume index -> `resumable_workflow`
- graph, branch, or large action sets -> `long_running_work`

Only `multi_step`, `resumable_workflow`, and `long_running_work` persist an operational plan in Phase 16.

## Plan Model

`TaskPlan` stores:

- plan id
- task id
- title and objective
- creation and update timestamps
- plan status
- task classification
- current step id
- total, completed, and failed step counts
- checkpoint pointer
- session and run ids
- linked execution receipt ids
- linked repair receipt ids
- plan steps

`PlanStep` stores:

- step id
- title and description
- step type
- dependency step ids
- status
- retry count
- started/completed timestamps
- failure summary
- expected outcome
- produced artifacts summary

## Step Lifecycle Model

Step statuses:

- `pending`
- `in_progress`
- `completed`
- `failed`
- `blocked`
- `skipped`
- `paused`

Plan statuses:

- `created`
- `active`
- `paused`
- `completed`
- `failed`
- `blocked`
- `cancelled`

The tracker computes plan progress explicitly from current step states rather than from hidden runtime state.

## Checkpoint Model

`PlanCheckpoint` stores:

- checkpoint id
- plan id
- timestamp
- step id
- snapshot summary
- resumable state payload
- last outcome summary

Checkpoint payloads are intentionally compact:

- long strings are truncated
- nested dictionaries are shallowly summarized
- large lists are clipped

This keeps persisted state small and resumable.

## Resume Model

The resume engine returns one of:

- `resume_from_checkpoint`
- `restart_current_step`
- `rebuild_plan`
- `manual_intervention_required`

Resume is refused when:

- the latest checkpoint points to a missing step
- plan dependencies are inconsistent
- no runnable next step can be identified safely

## Operational Summary Model

Each persisted summary includes:

- current objective
- plan status
- completed steps
- current step
- last failure
- next recommended action
- resumability state
- linked execution receipts
- linked repair receipts

This summary is intended for next-turn continuity and internal runtime diagnostics.

## Persistence Strategy

Phase 16 persists operational planning artifacts under:

- `.logs/fusion-runtime/planning/plans/`
- `.logs/fusion-runtime/planning/checkpoints/`
- `.logs/fusion-runtime/planning/summaries/`

Storage is plain JSON / JSONL and does not require a database.

## Integration Points

The planning layer is integrated additively into `backend/python/brain/runtime/orchestrator.py`.

Current integration behavior:

1. classify each runtime action batch
2. create an operational plan when work is multi-step or resumable
3. update plan state as action steps start and finish
4. link trusted execution receipts and repair receipts to the plan
5. write planning summaries to the runtime event log
6. consult the resume engine during `resume_run`

This keeps the Phase 14 and Phase 15 contracts intact while adding continuity.

## Safety Constraints

Phase 16 is deliberately conservative:

- planning is deterministic and inspectable
- non-plannable work does not get forced into persisted plans
- checkpoints are compact
- resume fails safe on inconsistency
- operational planning does not replace trusted execution or repair governance

## Limitations

Phase 16 does not yet implement:

- strategic replanning across arbitrary future turns
- learning-driven plan optimization
- multi-agent planning governance
- broad semantic memory replay
- autonomous strategy evolution

It is a continuity layer, not an autonomy overhaul.

## How This Prepares Later Phases

Phase 16 provides the durable operational spine needed for later work:

- steps are explicit and auditable
- runtime progress survives interruptions
- retries and repairs now sit inside resumable task context
- future phases can add smarter planning heuristics, policy learning, and richer coordination on top of this persisted operational state

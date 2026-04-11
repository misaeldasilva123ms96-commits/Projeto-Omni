# Phase 17 - Adaptive Continuation Layer

## Mission

Phase 17 adds the bounded decision layer that evaluates operational plan health and decides what Omni should do next after a step result, repair outcome, checkpoint transition, or resume event.

The goal is not free-form strategic autonomy. The goal is deterministic operational continuation:

- continue when safe
- retry when bounded retry remains appropriate
- pause when continuation is unsafe but resumable
- rebuild a remaining plan segment conservatively
- escalate when safe continuation is blocked
- complete when the objective is operationally satisfied

## Continuation Philosophy

The adaptive continuation layer follows these principles:

1. deterministic evidence over vague intuition
2. explicit decisions over hidden control flow
3. safe pause or escalation over risky continuation
4. bounded replan over broad redesign
5. persisted artifacts for every evaluation and decision

## Architecture

The layer lives in `backend/python/brain/runtime/continuation/`:

- `models.py`
  - continuation policy, evaluation, decision, and plan-health types
- `continuation_policy.py`
  - deterministic policy defaults and retry/replan gates
- `plan_evaluator.py`
  - plan health evaluation from current planning and receipt state
- `continuation_decider.py`
  - explicit decision ordering
- `replan_engine.py`
  - bounded replan of the remaining plan segment only
- `pause_handler.py`
  - safe pause behavior with resumability preservation
- `escalation_handler.py`
  - structured escalation artifact persistence
- `continuation_executor.py`
  - coordinator that evaluates, decides, persists, and applies bounded continuation actions

## Evaluation Model

`PlanEvaluation` captures:

- plan id
- current step id
- plan health
- progress ratio
- failed step count
- blocked step count
- retry pressure
- repair outcome summary
- resumability state
- dependency health
- recent receipt summary
- recommendation hints
- timestamp

Current plan health values:

- `healthy`
- `degraded`
- `stalled`
- `blocked`
- `completed`

## Decision Model

`ContinuationDecision` captures:

- decision id
- plan id
- task id
- step id
- decision type
- reason code
- reason summary
- confidence score
- recommended action
- timestamp
- linked execution receipt ids
- linked repair receipt ids
- linked checkpoint id

Decision types:

- `continue_execution`
- `retry_step`
- `pause_plan`
- `rebuild_plan`
- `escalate_failure`
- `complete_plan`

## Policy Model

Phase 17 uses conservative environment-driven defaults:

- `OMINI_CONTINUATION_MAX_RETRIES_PER_STEP=2`
- `OMINI_CONTINUATION_ALLOW_REPLAN=true`
- `OMINI_CONTINUATION_ALLOW_AUTO_PAUSE=true`
- `OMINI_CONTINUATION_ALLOW_AUTO_ESCALATE=true`
- `OMINI_CONTINUATION_MAX_REPLANS_PER_PLAN=1`

The policy constrains:

- retry budget
- replan budget
- pause permission
- escalation permission

## Decision Ordering

The current deterministic priority order is:

1. complete if the plan is finished
2. escalate if the plan is blocked or continuation is unsafe
3. pause if dependencies or resumability make safe continuation unavailable
4. rebuild if a bounded replan is available for the remaining segment
5. retry if bounded retry remains safe
6. continue otherwise

## Pause Model

When the runtime pauses:

- the current step is marked paused
- a planning checkpoint is written
- resumability metadata is preserved
- an updated operational summary is stored

This is used when continuation is uncertain but not terminal.

## Escalation Model

When the runtime escalates:

- the plan is marked blocked
- an escalation artifact is written under `.logs/fusion-runtime/continuation/escalations/`
- a checkpoint is preserved
- the operational summary is updated

This is used when retry, repair, or bounded replan are no longer safe.

## Replan Model

Phase 17 only allows bounded replans of the remaining plan segment.

Current bounded replan behavior:

- mark the failed step as skipped
- insert a replacement `validate_result` step
- rewire only downstream dependencies that referenced the failed step
- increment the per-plan replan count

Phase 17 does not permit broad workflow synthesis or cross-runtime redesign.

## Persistence Model

Artifacts are stored under:

- `.logs/fusion-runtime/continuation/decisions/`
- `.logs/fusion-runtime/continuation/evaluations/`
- `.logs/fusion-runtime/continuation/escalations/`

All artifacts are compact JSON or JSONL and align with the lightweight persistence model introduced in Phase 16.

## Integration Points

The continuation layer integrates additively with:

- Phase 16 planning state
- Phase 14 execution receipts
- Phase 15 repair receipts
- the Python orchestrator action-execution boundary

Current orchestrator behavior:

- after a step result is recorded into the plan, continuation evaluates the plan
- the decision is persisted and emitted as `runtime.continuation.decision`
- the result receives `continuation_decision`
- pause, replan, escalation, and completion can stop the current continuation safely

## Limitations

Phase 17 deliberately does not implement:

- learning-based adaptive policies
- unrestricted replanning
- multi-agent arbitration
- strategic reasoning overhaul
- autonomous architecture redesign

It is still a bounded operational control layer.

## How This Prepares Phase 18

Phase 17 provides the decision substrate for the next level of runtime resilience:

- plans now have explicit health
- continuation behavior is policy-governed and auditable
- retries, pauses, replans, and escalations are now first-class artifacts

Phase 18 can build on this by improving continuity quality across longer horizons without giving up the deterministic safety spine established in Phases 14 through 17.

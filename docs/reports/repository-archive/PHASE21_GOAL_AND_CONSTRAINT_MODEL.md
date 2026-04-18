# PHASE 21 — Goal & Constraint Model

## Mission

Phase 21 introduces the first runtime-core goal layer for Omni. The runtime no longer acts only because a task exists. It now carries an explicit goal anchor with bounded success logic, constraints, tolerances, and stop conditions that can be consulted by planning, continuation, learning, evolution, and orchestration.

## Goal Philosophy

The central principle of this phase is stability of intent under changing execution paths.

- Plans may change.
- Routes may change.
- Repairs may happen.
- Continuation may adapt.
- The active goal remains the anchor.

This keeps Omni goal-oriented without moving into uncontrolled autonomy.

## Conceptual Model

Phase 21 adds six core runtime objects:

- `Goal`
- `SubGoal`
- `Constraint`
- `SuccessCriterion`
- `FailureTolerance`
- `StopCondition`

Together they formalize:

- what Omni is trying to achieve
- what boundaries must not be crossed
- what partial failure is acceptable
- when execution must stop
- how progress should be measured

## Technical Model

The implementation lives in:

- `backend/python/brain/runtime/goals/__init__.py`
- `backend/python/brain/runtime/goals/models.py`
- `backend/python/brain/runtime/goals/goal_store.py`
- `backend/python/brain/runtime/goals/goal_factory.py`
- `backend/python/brain/runtime/goals/goal_evaluator.py`
- `backend/python/brain/runtime/goals/constraint_registry.py`
- `backend/python/brain/runtime/goals/goal_context.py`
- `backend/python/brain/runtime/goals/goal_sync.py`

### Goal

`Goal` is the primary runtime object and includes:

- id
- description
- intent
- subgoals
- constraints
- success criteria
- failure tolerances
- stop conditions
- status
- priority
- timestamps

### SubGoal

`SubGoal` is first-class and supports dependency-aware graphs via:

- `depends_on_subgoal_ids`

Phase 21 uses this conservatively, but it prepares the runtime for richer dependency-driven goal execution later.

### Constraint Model

Constraints are typed and severity-aware.

Supported types:

- `scope_limit`
- `resource_limit`
- `safety_limit`
- `compatibility`
- `time_limit`

Supported severities:

- `hard`
- `soft`

Hard violations can fail bounded continuation or block evolution. Soft violations are surfaced explicitly without silently killing execution.

### Success Criteria

Success criteria are weighted, typed, and deterministic.

Supported types:

- `structural`
- `functional`
- `evaluative`
- `composite`

Required criteria determine achievement. Optional criteria contribute to progress, but they do not prevent achievement by themselves.

### Failure Tolerances

Supported tolerance types:

- `max_retries`
- `max_repairs`
- `error_rate`
- `partial_success`

These make it possible to model bounded degradation without losing explicit control.

### Stop Conditions

Supported stop condition types:

- `max_cycles`
- `timeout`
- `resource_exhausted`
- `external_signal`
- `dependency_failed`

Stop conditions do not silently mutate execution. They surface explicit pause/stop signals for downstream runtime control.

## Persistence Model

Phase 21 uses a local-first persistence design.

Primary store:

- `.logs/fusion-runtime/goals/goal_store.json`

Characteristics:

- in-memory runtime state
- deterministic JSON persistence
- no external dependency on the critical path
- explicit reload and flush operations

Secondary optional export:

- `.logs/fusion-runtime/goals/goal_sync_export.jsonl`

`goal_sync.py` is intentionally non-blocking and advisory. Sync failure never breaks runtime execution.

## Concurrency Considerations

`GoalStore` is protected by `threading.RLock`.

The store is designed to be safe for:

- concurrent in-process writes
- concurrent status updates
- concurrent reload/flush access

Flushes are serialized under the same lock, which prevents interleaved in-memory mutation during persistence.

## Evaluation Model

`GoalEvaluator` runs in a fixed deterministic order:

1. constraints
2. stop conditions
3. failure tolerances
4. success criteria
5. final progress score

Evaluation output includes:

- `should_stop`
- `should_fail`
- `is_achieved`
- `progress_score`
- violated constraints
- triggered stop conditions
- unmet criteria
- reasoning

The `progress_score` is bounded to `0.0–1.0` and is reusable by continuation, learning, and future simulation layers.

## GoalContext

`GoalContext` is an immutable execution snapshot.

It captures:

- goal id
- description
- intent
- active constraints
- success criteria descriptions
- stop condition descriptions
- status
- priority

It also exposes `to_prompt_block()` so the runtime can inject goal state into prompt/context construction without allowing mid-cycle mutation.

## Integration Points

### Planning

Planning is no longer goal-agnostic.

- plans now carry `goal_id`
- planning creates or infers a goal via `GoalFactory`
- action steps can reference `subgoal_id`
- goal prompt data is stored in plan metadata

### Continuation

Continuation now checks goal state before regular continuation policy:

- achieved goal -> complete plan
- hard goal failure -> escalate/block
- triggered stop condition -> pause plan
- otherwise continue through existing continuation logic

### Learning

Learning evidence now includes:

- `goal_id`

This allows operational patterns to be indexed by the goal they served.

### Evolution

Governed evolution now consults active goal constraints when a goal is available.

- out-of-bound proposals can be blocked early
- evolution remains subordinate to goal boundaries

### Orchestration

Orchestration context now accepts optional `goal_context`.

This is None-safe and prepares the runtime for later cognitive specialization without breaking existing flows.

## Limitations

Phase 21 is intentionally conservative.

- Goal inference is deterministic and simple.
- Goal sync is export-only and local-first.
- Constraint evaluators are registry-driven and bounded, not semantic.
- Subgoal graphs are supported structurally, but only lightly consumed in this phase.
- No semantic memory, simulation, or specialist routing is introduced yet.

## How Phase 21 Prepares Phase 22

Phase 21 creates the stable anchor needed for deeper cognition.

With explicit goals and bounded progress measurement, later phases can build:

- memory indexed by goal trajectories
- richer continuity across turns
- stronger observability around objective progress
- future simulation or reasoning layers that evaluate alternatives against the same goal anchor

Phase 22 can now build on a runtime that knows not only what it is doing, but why it is doing it and what boundaries define success.

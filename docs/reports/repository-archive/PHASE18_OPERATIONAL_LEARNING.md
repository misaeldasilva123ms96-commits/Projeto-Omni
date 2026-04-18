# Phase 18 - Operational Learning Layer

## Mission

Phase 18 introduces a bounded operational learning layer that turns existing runtime artifacts into explicit evidence, compact pattern records, ranked bounded strategies, and advisory learning signals for future runtime decisions.

The goal is not opaque autonomy. The goal is auditable improvement from observed execution, repair, planning, checkpoint, and continuation outcomes.

## Learning Philosophy

The operational learning layer follows these principles:

1. structured runtime artifacts over free-form interpretation
2. advisory influence before policy override
3. deterministic aggregation over opaque scoring
4. bounded known strategy classes over invented strategies
5. compact persistent artifacts over uncontrolled memory growth

## Architecture

The layer lives in `backend/python/brain/runtime/learning/`:

- `models.py`
  - learning evidence, pattern, ranking, signal, and policy types
- `artifact_ingestor.py`
  - collects execution, repair, planning, checkpoint, and continuation artifacts
- `evidence_normalizer.py`
  - converts runtime artifacts into normalized `LearningEvidence`
- `pattern_registry.py`
  - generates bounded pattern keys for execution, repair, continuation, resume, and planning
- `outcome_aggregator.py`
  - computes deterministic operational statistics
- `strategy_ranker.py`
  - ranks known strategy classes from observed evidence
- `learning_policy.py`
  - environment-driven learning defaults
- `learning_signal_builder.py`
  - emits explicit advisory signals from ranked patterns
- `learning_store.py`
  - persists evidence, patterns, signals, and snapshots
- `learning_executor.py`
  - coordinates ingestion, normalization, aggregation, ranking, and signal emission

## Evidence Model

`LearningEvidence` captures:

- source type
- source artifact id
- session id
- task id
- plan id
- step id
- action type
- capability or tool
- subsystem
- outcome class
- success flag
- failure class
- retry count
- repair attempted flag
- repair promoted flag
- continuation decision type
- timestamp

Current source types:

- `execution_receipt`
- `repair_receipt`
- `plan_checkpoint`
- `operational_summary`
- `continuation_decision`
- `continuation_evaluation`

## Normalization Model

Phase 18 uses deterministic normalization rules:

- execution success plus verification success becomes positive execution evidence
- execution failure or verification failure becomes negative execution evidence
- repair promoted or validated becomes positive repair evidence
- repair rejection becomes negative repair evidence
- continuation decisions and evaluations become continuation evidence
- checkpoints and summaries become planning or resume evidence

The layer prefers structured fields already emitted by Phases 14 through 17.

## Pattern Registry Model

Pattern keys are compact and bounded. Current pattern categories include:

- execution:
  - `action_type + tool + subsystem + outcome_class`
- repair:
  - `repair_strategy + failure_class + target`
- continuation:
  - `decision_type + plan_health + dependency_health`
- resume:
  - `resume_decision + checkpoint outcome`
- planning:
  - `plan outcome + resumability state`

Each `PatternRecord` tracks:

- success count
- failure count
- total count
- success ratio
- recurrence count
- first seen
- last seen
- recent timestamps

## Ranking Model

Strategy ranking is bounded to known categories:

- preferred repair strategy
- preferred continuation decision
- discouraged retry pattern
- resume confidence hint
- step template success hint

Rankings are generated only when:

- learning is enabled
- enough samples exist
- the pattern is not stale

## Learning Signal Model

`LearningSignal` includes:

- signal id
- signal type
- source pattern key
- confidence
- weight
- recommendation
- evidence summary
- timestamp
- advisory flag

In Phase 18, signals are advisory by default.

## Policy Model

Current conservative defaults:

- `OMINI_LEARNING_ENABLED=true`
- `OMINI_LEARNING_MIN_PATTERN_SAMPLES=3`
- `OMINI_LEARNING_MAX_SIGNAL_WEIGHT=0.30`
- `OMINI_LEARNING_ALLOW_POLICY_HINTS=true`
- `OMINI_LEARNING_ALLOW_STRATEGY_RANKING=true`
- `OMINI_LEARNING_STALE_PATTERN_DAYS=30`

This keeps learning bounded and prevents weak or stale patterns from dominating runtime behavior.

## Integration Points

The learning layer integrates additively with:

- Phase 14 trusted execution receipts
- Phase 15 repair receipts
- Phase 16 planning checkpoints and summaries
- Phase 17 continuation evaluations and decisions

Current orchestrator behavior:

- ingest learning evidence after action execution results
- ingest learning evidence after continuation decisions
- ingest planning checkpoints and operational summaries at plan finalization
- attach advisory learning hints to the action result payload

Current downstream advisory use:

- planning may insert a bounded validation step after tools with historical validation benefit
- self-repair proposal confidence can be nudged by preferred repair strategy signals
- continuation confidence can be nudged by preferred or discouraged continuation signals

## Persistence Model

Artifacts are stored under:

- `.logs/fusion-runtime/learning/evidence/`
- `.logs/fusion-runtime/learning/patterns/`
- `.logs/fusion-runtime/learning/signals/`
- `.logs/fusion-runtime/learning/snapshots/`

All artifacts are compact JSON or JSONL and remain auditable.

## Limitations

Phase 18 deliberately does not implement:

- model fine-tuning
- free-form policy evolution
- unrestricted strategy synthesis
- architecture self-modification
- hidden adaptive overrides

It is still a bounded evidence and advisory layer.

## How This Prepares Phase 19

Phase 18 provides the first reusable operational learning substrate:

- runtime evidence is normalized consistently
- recurring patterns are aggregated deterministically
- advisory signals can now shape future bounded decisions

Phase 19 can build on this by improving cross-run operational memory and richer continuity reasoning while preserving explicit policy and auditability.

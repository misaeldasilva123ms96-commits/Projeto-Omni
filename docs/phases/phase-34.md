# Phase 34 — Runtime Learning System

Phase 34 adds a **bounded post-execution learning layer** that turns each completed chat-path turn into **structured evidence** (signals + assessment + persistence), without mutating strategy, prompts, or orchestration policy.

## Implemented Scope

- **`LearningEngine`** (`brain/runtime/learning/learning_engine.py`): after response + heuristic `evaluation`, derives:
  - **`RuntimeFeedbackSignal`** entries per stage: reasoning validation, memory presence, planning readiness, execution quality (incl. safe-fallback detection), latency bucket, runtime fallback hints.
  - **`ExecutionOutcomeAssessment`**: `success` / `degraded` / `failure` from grounded rules (fallback text, signal polarity counts, swarm empty, evaluation hints).
  - **`RuntimeLearningRecord`**: record id, session/run linkage, reasoning/plan trace ids when present, full signal list (capped in `as_dict()`), summary counts, `persisted` flag.
  - **`RuntimeLearningTrace`**: compact observability for audit readers.
- **Persistence** (`RuntimeLearningStore`): append-only JSONL at  
  `.logs/fusion-runtime/learning/evidence/runtime_turn_records.jsonl`  
  Failures to write do **not** break the orchestrator; `persisted=False` on the record/trace.
- **Runtime integration** (`BrainOrchestrator.run`): after `evaluator.evaluate`, computes turn `duration_ms`, calls `LearningEngine.assess_chat_turn`, emits **`runtime.learning_intelligence.trace`** on `execution-audit.jsonl`, and stores **`runtime_learning`** on the session payload.
- **Observability**: `read_recent_learning_intelligence_traces` / `read_latest_learning_intelligence_trace` + `ObservabilitySnapshot` fields, aligned with Phases 31–33 trace patterns.

## Coexistence with existing learning

The repository already has **`LearningExecutor`** + pattern **`LearningSignal`** (repair/continuation advisories). Phase 34 uses **separate types** (`RuntimeFeedbackSignal`, `RuntimeLearningRecord`) so operational pattern learning remains unchanged.

## What Phase 34 explicitly does *not* do

- **Phase 35 — Strategy adaptation**: no automatic strategy or routing mutation from records.
- **Performance / multi-agent / self-evolution phases**: not started.
- **Online prompt or contract rewriting**: not performed.
- **Heavy analytics stack**: only file-backed JSONL append.

## Flow

```text
… → execution / response → evaluation → LearningEngine → record + trace → audit + session
```

## Verification

Run `tests/runtime/learning/test_learning_engine.py` plus reasoning / planning / observability / orchestrator integration regressions.

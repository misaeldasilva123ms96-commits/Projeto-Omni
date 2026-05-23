# Phase 36 — Performance Optimization Layer

Phase 36 adds a **bounded, observable performance layer** focused on the **Python → Node/swarm boundary**: structured compression of the `context_session` payload, an **in-process LRU cache** of slim handoffs for identical bounded fingerprints, and **`runtime.performance_optimization.trace`** audit entries with estimated byte deltas.

## Implemented Scope

- **`PerformanceEngine`** (`brain/runtime/performance/performance_engine.py`): builds a **slim swarm context** (compression) and optionally serves it from an **LRU cache** keyed by `(session_id, message prefix, memory context_id, intent, plan_id)` fingerprint.
- **`compression.py`**: deterministic, inspectable slimming of:
  - `memory_intelligence` (truncated summary, reduced `scoring`),
  - `reasoning_handoff` (truncated summaries, capped steps/capabilities),
  - `execution_plan` (truncated step descriptions, capped steps/checkpoints/fallbacks),
  - `planning_trace` (high-signal fields only),
  - `structured_memory` (bounded list/dict walk with depth guard).
- **`metrics.py`**: UTF-8 JSON length estimates for before/after comparisons.
- **`cache.py`**: `BoundedLRUCache` (default 48 entries, in-process only).
- **Orchestrator** (`BrainOrchestrator.run`):
  - Swarm path: `_budget_to_dict` / `_retrieval_plan_to_dict` computed **once** per turn and fed into `PerformanceEngine.optimize_swarm_boundary`; **slim context** passed to the swarm executor.
  - Direct-memory path: emits a **skipped** performance trace (no swarm compression).
  - **Learning** still receives **full** memory/planning dicts (governance/evidence preserved).
  - Session payload gains `performance_optimization` with `{trace, stats}`.
- **Observability**: `read_recent_performance_optimization_traces` / snapshot fields.

## Non-goals

- **Phase 37+** multi-agent coordination, autonomous decomposition, self-evolution.
- **Answer replay caching** (explicitly not the focus).
- **Removing or weakening** reasoning, planning, strategy, control, or audit trails.

## Fallback / Safety

Compression or cache failures fall back to an **uncompressed** swarm context with `phase36_boundary: fallback_uncompressed` and `degraded` trace flags — runtime continues.

## Verification

Run `tests/runtime/performance/test_performance_engine.py` plus Phase 31–35 regression tests touching orchestrator, learning, and observability.

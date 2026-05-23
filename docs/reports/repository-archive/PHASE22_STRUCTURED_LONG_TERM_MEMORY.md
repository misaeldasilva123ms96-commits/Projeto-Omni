# Phase 22 - Structured Long-Term Memory

## Mission

Phase 22 turns Omni into a memory-capable cognitive runtime without introducing an opaque memory blob. The runtime now keeps bounded, goal-oriented memory across four explicit layers:

- working memory
- episodic memory
- semantic memory
- procedural memory

The design remains local-first, deterministic, auditable, and safe for future simulation work.

## Memory Philosophy

The memory model follows a simple rule: memory must stay interpretable.

- Working memory captures active session state only.
- Episodic memory stores durable goal-bound runtime episodes.
- Semantic memory consolidates generalized facts only after evidence thresholds are met.
- Procedural memory stores reusable route recommendations derived from prior outcomes.

Python owns all runtime-critical memory operations. Bun remains outside the critical path for this phase.

## Four Memory Types

### Working Memory

Working memory is volatile session state with explicit lifecycle controls.

- storage: in-memory plus JSON flush
- file: `.logs/fusion-runtime/memory/working_memory.json`
- lifecycle:
  - `start_new_session(...)`
  - `close_session()`
  - `reset_session()`

It stores:

- `session_id`
- `goal_id`
- `active_plan_id`
- bounded `recent_events`
- `active_constraints`
- `current_progress`

### Episodic Memory

Episodic memory persists bounded runtime episodes tied to goals.

- storage: SQLite via `sqlite3`
- file: `.logs/fusion-runtime/memory/db/episodic.db`
- schema is initialized deterministically
- write access is protected with `threading.RLock`

Episodes include:

- goal and session identity
- event type and outcome
- progress window
- active constraints
- linked evidence ids
- compact metadata

### Semantic Memory

Semantic memory stores generalized facts consolidated from episodes.

- storage: SQLite via `sqlite3`
- file: `.logs/fusion-runtime/memory/db/semantic.db`
- consolidation is threshold-gated

Defaults:

- `OMINI_MEMORY_MIN_EPISODES_FOR_SEMANTIC_FACT=5`
- `OMINI_MEMORY_MIN_CONFIDENCE_FOR_SEMANTIC_RECALL=0.6`

Facts are stored as explicit triples:

- `subject`
- `predicate`
- `object`

Each fact retains its source episode references and confidence.

### Procedural Memory

Procedural memory stores reusable process recommendations.

- storage: JSON
- file: `.logs/fusion-runtime/memory/procedural_patterns.json`

Patterns remain bounded and explicit:

- applicable goal types
- applicable constraint types
- recommended route
- success rate
- sample size

## Storage Strategy

Phase 22 uses a mixed persistence model:

- WorkingMemory -> in-memory + JSON
- EpisodicMemory -> SQLite
- SemanticMemory -> SQLite
- ProceduralMemory -> JSON

Python remains the source of truth for all runtime-critical memory operations.

## WAL and Concurrency Strategy

Both SQLite stores use:

- `PRAGMA journal_mode=WAL`
- `PRAGMA synchronous=NORMAL`

Write access is guarded with `threading.RLock`.

Because some Windows/OneDrive environments can reject WAL-backed SQLite files under the repository path, the stores include a conservative fallback to a deterministic temp-directory mirror. This fallback is only used when the preferred local path raises an operational I/O error during initialization. The runtime API remains unchanged.

## Runtime Integration Points

### Orchestrator

The orchestrator now initializes a single `MemoryFacade` and reuses it across the runtime.

It currently:

- activates working memory when a goal-aware plan is created
- records plan initialization
- updates progress on continuation outcomes
- closes goal episodes on completion or escalation

### Continuation

Continuation now records:

- decision type
- reason summary
- progress ratio
- linked evidence ids

This feeds working memory directly and keeps the continuation layer goal-aware over time.

### Learning

Learning already indexed `goal_id`; Phase 22 extends that by recording evidence-linked working-memory events when goal-bound evidence is ingested.

### Goal Evaluator

`GoalEvaluator` remains None-safe and deterministic.

When memory is available, it may now expose bounded `historical_context`:

- similar episodes
- procedural recommendation
- semantic facts

If memory is absent or lookup fails, behavior stays exactly as before.

## Memory Facade

`MemoryFacade` is the only runtime-facing entrypoint for this phase.

It exposes:

- `set_active_goal(...)`
- `record_event(...)`
- `update_progress(...)`
- `close_goal_episode(...)`
- `recall_similar(...)`
- `get_procedural_recommendation(...)`
- `get_semantic_facts(...)`

This keeps the rest of the runtime decoupled from storage ownership.

## Why Python Owns Primary Memory Operations

Memory in Omni is now part of runtime correctness.

That means:

- goal evaluation may consult memory
- continuation records memory events
- learning updates memory context
- orchestrator closes durable episodes

Those operations must remain local, synchronous enough for correctness, and independent of JS tooling availability. Bun/JS may be added later for tooling or inspection helpers, but not as owners of persistence or recall in this phase.

## Limitations

- Semantic consolidation is intentionally simple and threshold-based.
- Procedural recommendations remain route-level and bounded.
- No vector DB, embedding recall, or opaque synthesis exists in this phase.
- SQLite may fall back to a deterministic temp mirror on Windows/OneDrive WAL failures.
- Bun memory tooling is intentionally omitted because Python owns the critical path.

## How This Prepares Phase 23

Phase 22 establishes the interfaces Phase 23 needs without implementing simulation yet:

- `recall_similar(event_type, progress)`
- `get_procedural_recommendation(goal_type)`
- `get_semantic_facts(subject)`

That gives the next phase durable historical context, reusable route hints, and safe generalized knowledge without sacrificing auditability.

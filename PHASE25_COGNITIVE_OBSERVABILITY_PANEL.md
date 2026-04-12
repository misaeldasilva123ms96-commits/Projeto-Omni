# Phase 25 - Cognitive Observability Panel

## Mission

Phase 25 exposes the Omni cognitive runtime in a product-facing, audit-friendly, strictly read-only surface. The purpose of this phase is legibility, not control: operators, developers, and product stakeholders can inspect the runtime without altering planning, continuation, memory, simulation, or specialist behavior.

## Observability Philosophy

The runtime already persists rich cognitive artifacts:

- goals and constraints
- working memory session state
- episodic, semantic, and procedural memory
- simulation results
- specialist coordination traces
- learning and evolution side signals

Phase 25 does not rebuild those layers. It reads them safely, aggregates them conservatively, and presents them in a stable contract for Rust and React.

Core principle:

- expose, do not reinvent

## Why This Layer Is Read-Only

Observability is intentionally isolated from runtime mutation paths.

- readers never call runtime write APIs
- observability SQLite access uses independent readonly connections
- Rust endpoints only invoke the Python CLI bridge for read operations
- the frontend only consumes REST/SSE payloads

This separation keeps observability safe during live execution and prepares the system for future operator-facing productization without coupling UI behavior to runtime internals.

## Panel Breakdown

The panel is composed of five bounded views:

1. Goal State Panel
   - active goal, intent, status, priority, progress, constraints, criteria, subgoals
2. Operational Timeline
   - recent working-memory events, progress movement, continuation outcomes
3. Specialist Trace Viewer
   - latest coordination trace, specialist sequence, governance verdicts, recent trace history
4. Simulation and Memory Panel
   - latest simulation result, route estimates, recent episodes, semantic facts, active procedural pattern
5. Learning and Evolution Signals
   - recent learning signals, recent semantic reinforcements, procedural updates, pending evolution proposals

Each panel renders gracefully when its backing artifacts are absent.

## Reader Architecture

Python owns the read layer under:

- `backend/python/brain/runtime/observability/`

Main readers:

- `goal_reader.py`
- `timeline_reader.py`
- `specialist_reader.py`
- `simulation_reader.py`
- `memory_reader.py`
- `observability_reader.py`
- `cli.py`

`ObservabilityReader` is the aggregation entrypoint. It composes the lower-level readers and emits a frontend-friendly `ObservabilitySnapshot`.

## JSON and JSONL Resilience Strategy

### Partial JSON protection

Some runtime JSON files may be read while an in-flight flush is happening. For JSON-backed artifacts such as:

- goal store
- working memory
- procedural registry

readers now:

- attempt parse once
- retry once after a short delay
- return empty/None-safe output if the file is still incomplete

One partial write does not crash the panel.

### Truncated JSONL tolerance

For append-only logs such as:

- simulation logs
- specialist coordination logs
- learning/evolution JSONL sources used by the panel

readers now:

- ignore empty lines
- skip invalid/truncated lines individually
- continue processing valid lines

### Tail-bounded reading

Observability readers do not naively read entire JSONL files.

They use bounded tail-reading logic that:

- seeks from the end of the file
- reads only a capped tail window
- returns the most recent valid entries needed for the panel

This keeps the panel bounded as audit logs grow.

## Readonly SQLite Strategy

Observability opens episodic and semantic databases with independent readonly connections.

Key properties:

- readonly URI mode
- no reuse of runtime write connections
- bounded queries only
- safe close after each read scope

This keeps inspection independent from runtime ownership and prevents accidental writes from observability code.

## Rust / Axum Bridge

Rust exposes additive routes:

- `GET /api/observability/snapshot`
- `GET /api/observability/traces?limit=N`
- `GET /api/observability/stream`

The bridge calls Python through:

- `python -m brain.runtime.observability.cli`

Safety behavior:

- explicit short timeout
- graceful JSON error payloads
- no panic path for transient Python failures
- SSE remains alive even if one snapshot read fails

## SSE Strategy

The live stream is SSE-based and intentionally simple.

Behavior:

- periodic snapshot events
- explicit heartbeat comments
- Axum keepalive enabled as secondary protection
- frontend connection states: idle, live, reconnecting, error

This is enough for a product-grade internal panel without adding websocket complexity.

## Frontend Structure

Frontend additions live under:

- `frontend/src/pages/ObservabilityPage.tsx`
- `frontend/src/components/observability/`
- `frontend/src/hooks/useObservabilitySnapshot.ts`
- `frontend/src/hooks/useObservabilityStream.ts`
- `frontend/src/types/observability.ts`

The page is additive and available at:

- `/observability`

The existing chat/dashboard flow remains intact.

## Limitations

Phase 25 is intentionally conservative.

- it does not add write controls
- it does not add auth/multi-tenant access control
- it does not add speculative analytics pipelines
- it does not add websocket orchestration or deep historical search UI
- it does not reinterpret cognitive logic beyond light display-oriented enrichment

The panel is only as current as the persisted artifacts already emitted by the runtime.

## Security

The observability surface is protected by Supabase Auth.

- `GET /api/observability/snapshot` requires a valid Supabase JWT
- `GET /api/observability/traces` requires a valid Supabase JWT
- `GET /api/observability/stream` requires a valid Supabase JWT
- the SSE endpoint accepts the token through `?token=` for browser `EventSource` compatibility
- `SUPABASE_JWT_SECRET` must be present in the Rust runtime environment or the API refuses to start
- issuer validation is derived from `SUPABASE_URL` (or `VITE_SUPABASE_URL` as a compatibility fallback)
- access-log spans redact the `token` query parameter so bearer material never appears in plaintext logs

Authenticated users retain the existing read-only behavior. Unauthenticated requests receive `401 unauthorized` and the frontend gates `/observability` behind the existing Supabase session.

## How This Prepares Later Productization

Phase 25 establishes the stable contracts needed for the next stage of product readiness:

- a read-only operator surface
- resilient artifact readers during live runtime activity
- safe Rust-to-Python observability bridging
- frontend contracts for cognitive state inspection
- SSE infrastructure for live product diagnostics

This creates a clean base for future authenticated operator tooling, richer diagnostics, and higher-level product observability without destabilizing the runtime core.

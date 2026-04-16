# Architecture

## Overview

Omni is a layered cognitive runtime.  
Each layer has a clear contract and bounded responsibility, with governance and observability integrated into control-plane reads.

```text
Client
  -> Rust API boundary
  -> Python runtime orchestration
  -> Node agent runtime
  -> Persisted control + memory state
```

## Runtime Layers

### 1) OIL Layer

Primary location: `backend/python/brain/runtime/language/`

- Defines typed runtime I/O contracts (`OILRequest`, `OILResult`, `OILError`)
- Normalizes input and composes output envelopes
- Preserves structured protocol boundaries across runtime flows

### 2) Orchestration Layer

Primary location: `backend/python/brain/runtime/`

- `BrainOrchestrator` coordinates planning, execution routing, specialists, continuation, learning, and governance integration
- Control-plane state is persisted through runtime services and registries
- Runtime behavior is governed through explicit transitions rather than implicit side effects

### 3) Node Agent Runtime

Primary locations: `js-runner/`, `src/`, runtime Node adapters

- Executes Node-based reasoning/agent logic
- Uses schema-validated payload contracts from Python
- Remains isolated behind explicit bridge interfaces

### 4) Memory Layer

Primary locations: `backend/python/brain/runtime/memory/`, `backend/python/memory/`, transcript/session stores

- Stores operational memory artifacts: sessions, transcripts, learning signals, and related snapshots
- Supports runtime recall and operational auditability
- Keeps memory persistence explicit and inspectable

### 5) Evolution Layer

Primary location: `backend/python/brain/runtime/evolution/`

- Governed proposal lifecycle (proposal, validation, explicit review, bounded application, rollback)
- Bounded sandbox mutation only (`.logs/fusion-runtime/evolution/sandbox`)
- No autonomous self-modification loop in production runtime paths

## Governance and Control Plane

Primary location: `backend/python/brain/runtime/control/`

- Canonical taxonomy: reason/source/severity
- Run-level source of truth: `RunRegistry`
- Read model: operational governance snapshot and attention views
- Strictly controlled transitions through explicit service/controller paths

## Observability

Primary location: `backend/python/brain/runtime/observability/`

- Consolidated runtime snapshot across goals, traces, simulations, governance, and governed evolution
- Stable read surfaces for operational tooling and CLI consumers
- Additive contract evolution with fallback-normalized shapes

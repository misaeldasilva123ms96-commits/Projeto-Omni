# Omni Architecture

## System overview

Omni is a multi-runtime system with a split execution model:

- Rust exposes the public HTTP/API boundary.
- Python coordinates the brain/runtime behavior.
- Node/Bun provides execution authority, planning output, and execution-request generation.

The repository is not a greenfield prototype. It already contains multiple layers for orchestration, control, observability, learning, and execution. The architecture is therefore best understood as a live runtime under audit and recovery, not as a finished product.

## Main layers

### Rust API layer

The Rust service receives client requests, manages the public API surface, invokes Python, and shapes the final response envelope.

Primary files:

- `backend/rust/src/main.rs`
- `backend/rust/Cargo.toml`

### Python brain runtime

Python is the main orchestration layer. It owns request coordination, runtime state, strategy dispatch, fallback behavior, observability emission, and cognitive runtime inspection.

Primary files:

- `backend/python/main.py`
- `backend/python/brain/runtime/orchestrator.py`
- `backend/python/brain/runtime/control/`
- `backend/python/brain/runtime/observability/`
- `backend/python/brain/runtime/language/`

### Node/Bun execution layer

Node/Bun handles the execution-side authority that can return:

- matcher shortcuts
- local direct responses
- bridge execution requests
- action-backed execution requests

Primary files:

- `js-runner/queryEngineRunner.js`
- `src/queryEngineRunnerAdapter.js`
- `core/brain/queryEngineAuthority.js`

### Observability layer

Observability is implemented mainly in Python, with persisted runtime traces and derived read models. The goal is to expose what path actually happened, not just whether the user received a response.

Primary files:

- `backend/python/brain/runtime/observability/`
- `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`
- `backend/python/brain/runtime/observability/runtime_lane_classifier.py`

### Governance layer

Governance and control decide what is allowed, how the runtime records operational decisions, and how degraded behavior is surfaced instead of hidden.

Primary files:

- `backend/python/brain/runtime/control/`
- `backend/python/brain/runtime/orchestrator_services/`
- `runtime/tooling/`

## Data flow

The real runtime path is:

1. User input arrives through Rust.
2. Rust invokes the Python entrypoint.
3. Python sanitizes the input envelope and calls `BrainOrchestrator.run(...)`.
4. Python builds runtime context and can delegate to Node.
5. Node may return a direct response, a bridge execution request, or an action-backed execution request.
6. Python may execute the returned actions and synthesize the final result.
7. Python emits runtime inspection and returns a safe JSON envelope.
8. Rust returns the public response.

## Runtime interaction

The three runtimes interact through explicit transport boundaries:

- Rust → Python by subprocess/stdin/stdout handoff
- Python → Node by subprocess/stdin/stdout handoff
- Node → Python by structured JSON payload

This architecture gives Omni flexibility, but it also creates failure modes around:

- contract drift
- output sanitization
- fallback masking
- execution-lane truthfulness

Those are active areas of public debugging.

## Current architectural reality

The architecture is real, but not fully recovered yet.

Today the repository contains:

- explicit semantic lane classification
- explicit execution-lane classification
- compatibility execution paths
- a real `true_action_execution` path
- audit documents that describe where the runtime is still unstable

For a simpler introduction, see:

- [docs/overview.md](docs/overview.md)
- [docs/architecture/layers.md](docs/architecture/layers.md)
- [docs/architecture/runtime-flow.md](docs/architecture/runtime-flow.md)
- [docs/architecture/runtime-modes.md](docs/architecture/runtime-modes.md)
- [docs/architecture/bridge-pipeline.md](docs/architecture/bridge-pipeline.md)
- [docs/architecture/bridge-response-contract.md](docs/architecture/bridge-response-contract.md)
- [docs/architecture/tool-runtime.md](docs/architecture/tool-runtime.md)
- [docs/architecture/cognitive-decision-model.md](docs/architecture/cognitive-decision-model.md)

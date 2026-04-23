# Omni Layers

## Rust API Layer

### Purpose

Provide the public HTTP/API boundary for Omni.

### Responsibilities

- receive chat requests
- maintain the public response envelope
- invoke the Python runtime
- forward runtime inspection when available

### Main files

- `backend/rust/src/main.rs`
- `backend/rust/Cargo.toml`

## Python Brain Runtime

### Purpose

Act as the central coordination layer for the Omni runtime.

### Responsibilities

- normalize and coordinate requests
- build runtime context and memory context
- perform routing and strategy dispatch
- call Node when needed
- execute runtime actions
- synthesize the final response
- emit runtime inspection and observability data

### Main files

- `backend/python/main.py`
- `backend/python/brain/runtime/orchestrator.py`
- `backend/python/brain/runtime/language/`
- `backend/python/brain/runtime/orchestrator_services/`

## Node/Bun Execution Layer

### Purpose

Provide execution-side planning and structured runtime responses.

### Responsibilities

- classify conversational shortcuts
- build execution plans
- emit execution requests
- return direct responses, bridge requests, or action-backed requests

### Main files

- `js-runner/queryEngineRunner.js`
- `src/queryEngineRunnerAdapter.js`
- `core/brain/queryEngineAuthority.js`

## Observability Layer

### Purpose

Show what actually happened during a runtime turn.

### Responsibilities

- classify semantic runtime lanes
- classify execution runtime lanes
- build cognitive runtime inspection
- expose snapshots, readers, and trace-friendly metadata

### Main files

- `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`
- `backend/python/brain/runtime/observability/runtime_lane_classifier.py`
- `backend/python/brain/runtime/observability/`

## Governance Layer

### Purpose

Keep execution bounded, auditable, and explicit.

### Responsibilities

- enforce tool and runtime control rules
- track run lifecycle and governance state
- preserve explicit fallback and downgrade behavior
- prevent hidden operational failures from looking like healthy execution

### Main files

- `backend/python/brain/runtime/control/`
- `backend/python/brain/runtime/orchestrator_services/`
- `runtime/tooling/`

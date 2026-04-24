# Bridge Response Contract

This document defines the minimum fields that must survive the full Omni pipeline.

## Minimum public fields

| Field | Required | Owning layer | Notes |
| --- | --- | --- | --- |
| `response` | yes | Python main / Rust boundary | Must be non-empty in the final public payload. |
| `runtime_mode` | yes, inside inspection | Python observability | Canonical runtime classification. |
| `runtime_reason` | yes, inside inspection | Python observability | Evidence-based reason for the selected mode. |
| `cognitive_runtime_inspection` | yes when available | Python observability, preserved by Rust | Main runtime truth envelope. |
| `signals` | yes, inside inspection | Python observability | Detailed truth-bearing signals. |
| `execution_path_used` | yes, inside `signals` | Python orchestrator | Example: `node_execution`, `local_tool_execution`, `rust_python_bridge`. |
| `fallback_triggered` | yes, inside `signals` | Python orchestrator / Rust fallback wrapper | Boolean boundary truth. |
| `compatibility_execution_active` | yes, inside `signals` | Python strategy execution | Distinguishes compatibility path from true action execution. |
| `provider_actual` | yes when known | Node provenance → Python inspection | Empty string when unknown. |
| `provider_failed` | yes when known | Node provenance → Python inspection | Explicit provider failure boolean. |
| `failure_class` | yes when error exists | Rust/Python/Node boundary that failed | Canonical bridge/runtime failure class. |
| `execution_provenance` | yes when known, inside `signals` | Node provenance, preserved by Python | Structured provenance payload. |
| `providers` | optional | Python main | Logical provider list, not secrets. |
| `error` | optional but required on structured failure | failing boundary | Additive public field for bridge/runtime failure details. |

## Boundary responsibilities

### Rust

- validates Python stdout
- rejects empty stdout as failure
- preserves:
  - `cognitive_runtime_inspection`
  - `providers`
  - `error`

### Python main

- emits one JSON object on stdout
- sanitizes internal runtime output into public shape
- adds `providers`
- emits structured `error` on boundary failure

### Python orchestrator

- builds truthful `cognitive_runtime_inspection`
- passes `execution_path_used`, fallback state, provenance, and compatibility signals

### Node runner

- returns one JSON object on stdout
- preserves structured `execution_request`
- preserves `error` if present
- never treats empty response as success

### Node authority

- sets provenance and runtime hint evidence
- distinguishes matcher, local direct, bridge, local tool, and action paths

## Canonical bridge failure classes

- `PYTHON_BRIDGE_EMPTY_STDOUT`
- `PYTHON_BRIDGE_INVALID_JSON`
- `PYTHON_BRIDGE_NONZERO_EXIT`
- `NODE_BRIDGE_EMPTY_STDOUT`
- `NODE_BRIDGE_INVALID_JSON`
- `NODE_BRIDGE_NONZERO_EXIT`
- `NODE_BRIDGE_TIMEOUT`
- `NODE_EMPTY_RESPONSE`
- `FRONTEND_RESPONSE_SHAPE_MISMATCH`

## Compatibility rule

The contract is additive:

- existing clients may keep reading `response`
- newer clients may inspect `error` and `cognitive_runtime_inspection.signals`
- no layer should rely on plain response text alone to infer runtime health

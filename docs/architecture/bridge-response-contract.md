# Bridge Response Contract

This document defines the minimum fields that must survive the full Omni pipeline.

## Current pipeline

Default audited path:

```txt
Rust/Axum HTTP
  -> Python subprocess `backend/python/main.py`
  -> Python `BrainOrchestrator`
  -> Node subprocess `js-runner/queryEngineRunner.js`
  -> public sanitization
  -> Rust HTTP response
```

Python and Node service modes exist behind configuration, but subprocess mode remains the default controlled-demo path.

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
| `runtime_truth` | yes when available | Node runtime truth, Python inspection | Evidence-bearing summary; lower-runtime claims are preserved but not blindly promoted. |
| `provider_diagnostics` | optional | Node/Python provider layers | Must expose public-safe booleans/status, not keys or raw provider payloads. |
| `tool_execution` | optional | Python/Node tool layers | Must distinguish selected/requested from attempted/executed/blocked. |
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
- treats HTTP 200 as transport success only, not cognitive success
- disables internal debug logging in public demo mode even when debug log level is set

### Python main

- emits one JSON object on stdout
- sanitizes internal runtime output into public shape
- adds `providers`
- emits structured `error` on boundary failure
- strips raw stack traces, command output, raw provider payloads, and secret-like fields from public output

### Python orchestrator

- builds truthful `cognitive_runtime_inspection`
- passes `execution_path_used`, fallback state, provenance, and compatibility signals
- preserves Node `runtime_truth`, intent, intent source, and classifier metadata through normalization

### Node runner

- returns one JSON object on stdout
- preserves structured `execution_request`
- preserves `error` if present
- never treats empty response as success
- emits public-safe debug output only when public demo mode is disabled

### Node authority

- sets provenance and runtime hint evidence
- distinguishes matcher, local direct, bridge, local tool, and action paths
- must not treat matcher, local direct, or compatibility execution as full cognitive runtime

## Public response shape

The exact response can be additive, but current callers should expect this shape when available:

```json
{
  "response": "public user-visible text",
  "status": "success or error-like public status",
  "providers": [],
  "provider_diagnostics": {},
  "tool_execution": {},
  "cognitive_runtime_inspection": {
    "runtime_mode": "MATCHER_SHORTCUT",
    "runtime_reason": "evidence-based reason",
    "runtime_truth": {},
    "signals": {},
    "public_summary": "safe summary"
  },
  "error": null
}
```

Fields may be `null`, absent, or empty when a lower runtime did not provide evidence. Missing diagnostics should prefer safe unknown/false behavior rather than false positive provider/tool success.

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

## Success masking rule

The following are not sufficient to claim cognitive success:

- HTTP 200
- valid JSON
- `status=success`
- `NODE_EXECUTION_SUCCESS`
- `strategy_dispatch_applied=true`
- non-empty assistant text

Full or partial cognitive claims require explicit runtime evidence from execution diagnostics, preserved Node runtime truth, provider diagnostics, tool execution diagnostics, and fallback/governance state.

## Sanitizer expectations

Public payloads must not expose:

- stack traces or tracebacks
- raw stdout/stderr
- shell commands or raw tool results
- raw provider payloads
- env dumps, API keys, tokens, JWTs, passwords, or secret-like values
- private memory content
- absolute sensitive paths

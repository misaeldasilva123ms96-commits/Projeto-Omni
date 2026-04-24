# Known Issues

## Execution collapse

Status: **PARTIALLY FIXED**

What changed:

- The orchestrator no longer treats `compat_execute()` as the only effective strategy-execution path.
- A primary node execution branch now exists and is attempted before compatibility fallback when the turn is execution-capable.
- Empty node responses are treated as failure in the recovered primary execution path.

What is still true:

- Compatibility execution still exists and remains necessary as a safe fallback path.
- Routing/classification can still choose conservative strategies for prompts that are actually tool-capable.
- Additional work is still needed to increase the activation rate and success rate for non-compat paths beyond the first recovered path.

## Current public debug focus

- improving strategy selection accuracy without hiding degraded behavior
- extending reliable non-compat execution beyond the first recovered path
- reducing generic or compatibility-heavy responses when execution evidence is available

## Runtime truth and classification

Status: **PARTIALLY FIXED**

What changed:

- `runtime_mode` is now derived from canonical evidence instead of generic transport success.
- `cognitive_runtime_inspection.signals` now exposes:
  - `runtime_reason`
  - `execution_path_used`
  - `fallback_triggered`
  - `compatibility_execution_active`
  - `provider_actual`
  - `provider_failed`
  - `failure_class`
  - `execution_provenance`
- matcher shortcuts, direct local responses, compatibility execution, Node failure, provider failure, and real action execution are now distinguishable in inspection.

What is still true:

- Some prompts still resolve to `COMPATIBILITY_EXECUTION` or `PARTIAL_COGNITIVE_RUNTIME`.
- The strongest path is now visible, but it is not yet dominant for every prompt family.
- Classification truth does not guarantee execution success; a truthful `true_action_execution` turn can still fail later in the tool/runtime layer.

## Bridge pipeline reliability

Status: **PARTIALLY FIXED**

What changed:

- Rust now rejects empty Python stdout and invalid Python JSON as structured bridge failures.
- Python main reserves stdout for a single JSON object and emits structured `error` payloads on boundary failures.
- Python → Node transport now classifies:
  - `NODE_BRIDGE_EMPTY_STDOUT`
  - `NODE_BRIDGE_INVALID_JSON`
  - `NODE_BRIDGE_NONZERO_EXIT`
  - `NODE_BRIDGE_TIMEOUT`
- Node runner now returns structured `error` payloads for empty/invalid result shapes instead of silently collapsing to plain fallback text.

What is still true:

- The executor layer can still fail after the bridge is healthy; that is a downstream execution failure, not a bridge parse failure.
- Frontend consumers still need to prefer `error` and `cognitive_runtime_inspection.signals` over plain response text for diagnostics.

## Frontend debug surface

Status: **PARTIALLY FIXED**

What changed:

- The chat UI now preserves runtime metadata from the backend response instead of dropping it in the wire adapter.
- The status panel exposes the last turn's:
  - `runtime_mode`
  - `runtime_reason`
  - `execution_path_used`
  - `fallback_triggered`
  - `compatibility_execution_active`
  - `provider_actual`
  - `provider_failed`
  - `failure_class`
  - presence of `cognitive_runtime_inspection`
  - presence of `execution_provenance`
- Structured error payloads from chat endpoints can now reach the frontend debug surface instead of collapsing to a generic text-only failure.

What is still true:

- The frontend can only show fields that survive the HTTP contract; if a backend route omits a field, the panel reports `n/a`.
- The chat UI is now a better first-stop diagnostic surface, but backend logs may still be needed for low-level executor failures.

## Provider diagnostics

Status: **PARTIALLY FIXED**

What changed:

- Omni now exposes a public-safe `provider_diagnostics` structure.
- The runtime can now distinguish:
  - configured providers
  - selected provider
  - attempted provider
  - provider failure vs bridge failure
  - provider fallback routing
  - no-provider-available state
- The frontend debug panel now surfaces this provider context directly.

What is still true:

- `configured` and `available` are currently configuration-level signals, not active network health checks.
- A selected provider does not guarantee an actual remote provider call happened on that turn.

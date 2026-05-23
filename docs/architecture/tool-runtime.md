# Tool Runtime

## Purpose

The tool runtime is the part of Omni that turns an execution-capable request into a real action result instead of a text-only response.

This layer does not decide *whether* the turn should be cognitive, fallback, or bridge-heavy. Its job is narrower:

- detect that a tool/action was requested
- choose the executable tool path
- execute the tool safely
- return a structured result
- expose enough diagnostics to explain failures

## Real flow

Current action flow:

1. `core/brain/queryEngineAuthority.js`
   - interprets the request
   - may emit `execution_request.actions`
2. `backend/python/brain/runtime/orchestrator.py`
   - receives the Node payload
   - routes action-backed turns into `_execute_runtime_actions(...)`
3. `backend/python/brain/runtime/orchestrator.py`
   - executes each action in `_execute_single_action_core(...)`
   - applies governance, policy, supervision, retries, and self-repair hooks
4. Execution backend
   - local engineering tools: `backend/python/brain/runtime/engineering_tools.py`
   - Rust-backed executor bridge: `backend/python/brain/runtime/rust_executor_bridge.py`
5. Result synthesis
   - `_synthesize_runtime_response(...)`
   - `build_cognitive_runtime_inspection(...)`
   - `backend/python/main.py`
   - Rust bridge and frontend

## Tool intent detection

Tool intent currently comes from a combination of:

- routing decision (`requires_tools`, `requires_node_runtime`)
- execution manifest step kinds
- selected tools in the manifest
- Node `execution_request.actions`

Primary routing is chosen in:

- `backend/python/brain/runtime/orchestrator.py`
  - `_select_primary_execution_type(...)`
  - `_dispatch_strategy_execution(...)`

## Where tool execution happens

### Local engineering tool path

Used when the selected tool is known to the Python local runtime.

Key files:

- `backend/python/brain/runtime/engineering_tools.py`
- `backend/python/brain/runtime/orchestrator.py`

Current local aliases supported directly in Python include:

- `read_file`
- `filesystem_read`
- `write_file`
- `filesystem_write`
- `glob_search`
- `code_search`
- `directory_tree`
- `git_status`
- `git_diff`
- `git_commit`
- `test_runner`
- `verification_runner`

### Rust-backed tool path

Used when the selected action is not handled by the local engineering tool surface.

Key files:

- `backend/python/brain/runtime/rust_executor_bridge.py`
- `backend/rust/src/main.rs`

## Tool execution diagnostics

Omni now emits a normalized tool diagnostic shape:

```json
{
  "tool_requested": true,
  "tool_selected": "read_file",
  "tool_available": true,
  "tool_attempted": true,
  "tool_succeeded": true,
  "tool_failed": false,
  "tool_denied": false,
  "tool_failure_class": null,
  "tool_failure_reason": null,
  "tool_latency_ms": 42
}
```

This shape is exposed in:

- `cognitive_runtime_inspection.signals.tool_execution`
- `cognitive_runtime_inspection.signals.tool_diagnostics`
- top-level chat response fields:
  - `tool_execution`
  - `tool_diagnostics`

## Failure classification

Tool failure should not be confused with provider or bridge failure.

Use this order:

1. `tool_execution.tool_denied`
   - policy/governance/operator denial
2. `tool_execution.tool_failed`
   - tool runtime failed after being attempted
3. `provider_failed`
   - provider-layer failure
4. `failure_class` / `runtime_reason`
   - bridge/runtime boundary failure

Examples:

- `permission_denied`
  - tool was selected, but not allowed
- `governed_tools_strict_block`
  - strict governed-tools mode blocked the tool
- `rust_bridge_failure`
  - tool path was attempted, but failed inside the Rust executor bridge

## Current status

What is stable now:

- tool/action execution is no longer silent
- tool attempts carry structured diagnostics
- local Python engineering tool aliases reduce unnecessary Rust-bridge dependency for common read/search actions
- frontend debug UI can display tool execution diagnostics for the last turn

What is still incomplete:

- not every tool-capable prompt routes to the optimal local tool path yet
- some Rust-backed actions can still fail after the pipeline and provider layers are healthy
- tool planning quality still depends on Node-side action selection behavior

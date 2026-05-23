# Runtime Modes

This document defines the canonical runtime modes used by Omni public debugging and runtime inspection.

The goal is to keep `runtime_mode` tied to evidence, not to generic transport success.

## Canonical modes

| Mode | Meaning | Required evidence | Common causes | Contributor notes |
| --- | --- | --- | --- | --- |
| `FULL_COGNITIVE_RUNTIME` | A real action-backed runtime completed with a complete cognitive chain. | Explicit provider/tool/action execution diagnostics, `semantic_runtime_lane=true_action_execution`, `execution_runtime_lane=true_action_execution`, `compatibility_execution_active=false`, `cognitive_chain=COMPLETE` | Node emitted `execution_request.actions` and Python executed them successfully. | This is the strongest healthy path currently available. |
| `PARTIAL_COGNITIVE_RUNTIME` / `PARTIAL_COGNITIVE` | A non-fallback result exists, but the evidence does not justify a full runtime claim. | Non-empty response plus explicit non-fallback evidence, but incomplete chain or bridge-only path. | Bridge execution request, partial planning, incomplete structured execution. | Do not confuse this with true action execution. |
| `NODE_EXECUTION_SUCCESS` | Node returned a usable action-oriented payload, but the turn did not meet the stricter full-runtime gate. | Node runtime truth and successful bridge transport, plus explicit execution evidence when claiming action execution. | Action path planned or executed, but planning/reasoning/chain completeness remained partial. | This is not automatically full cognitive success. |
| `LOCAL_TOOL_SUCCESS` | A local tool branch executed successfully without degrading to compatibility fallback. | `execution_runtime_lane=local_tool_execution` or Node hint `node_local_tool_run` plus success evidence. | Local tool execution path from Node authority or explicit local tool branch. | This is a real execution path, but it is distinct from Node action graph execution. |
| `MATCHER_SHORTCUT` | A matcher answered the turn without real execution. | `semantic_runtime_lane=matcher_shortcut` or explicit Node matcher hint. | Greeting and conversational shortcut matchers. | A valid response can still be operationally weak. |
| `DIRECT_LOCAL_RESPONSE` | A local direct response was returned without tool/action execution. | `semantic_runtime_lane=local_direct_response` | Memory reply, no-tool local answer, direct conversational path. | This is not a cognitive execution success. |
| `SAFE_FALLBACK` | The runtime intentionally returned the safe fallback path. | `fallback_triggered=true` or safe degraded lane without explicit Node failure evidence. | Governance block, compatibility fallback, empty operational path. | Safe fallback is truthful; it should not be hidden as success. |
| `SAFE_DEGRADED_FALLBACK` | Public-safe degraded fallback used when an upstream boundary cannot safely produce a stronger result. | Fallback or degraded stop reason from Rust/Python/Node diagnostics. | Bridge failure, invalid runtime output, governed block, provider/tool unavailable. | Treat as safe handling, not successful cognition. |
| `NODE_FAILURE` | The Node path failed or returned an unusable payload. | Node failure reason such as `timeout`, `subprocess_exception`, `empty_node_response`, `invalid_json` | Broken subprocess, empty Node payload, invalid structured response. | This is stronger than generic fallback because the Node failure is explicit. |
| `PROVIDER_FAILURE` | A provider-backed path failed and the failure is explicitly evidenced. | `execution_provenance.provider_failed=true` or `failure_class` indicates provider failure | Provider timeout, provider unavailable, upstream model failure. | Do not infer this from text alone. |
| `COMPATIBILITY_EXECUTION` | The turn completed through the compatibility path. Supported, but not the long-term happy path. | `compatibility_execution_active=true` or `execution_runtime_lane=compatibility_execution` | Strategy dispatch downgraded to compatibility runtime path. | This should remain visible in reports and bug filings. |

## Evidence hierarchy

Omni now resolves runtime truth in this order:

1. explicit failure evidence
2. explicit Python execution diagnostics and provenance
3. fallback flag
4. compatibility execution flag
5. preserved Node `runtime_truth` and classifier metadata
6. execution path used
7. safe default/unknown behavior

Response content, HTTP 200, valid JSON, `status=success`, and `NODE_EXECUTION_SUCCESS` are transport or boundary facts only. They must not promote a turn to `FULL_COGNITIVE_RUNTIME`.

## Provider and tool semantics

Provider and tool fields have separate meanings:

| Field family | Meaning |
| --- | --- |
| selected/planned/requested | A lower runtime chose or described a possible provider/tool path. |
| attempted | The runtime has explicit evidence that execution was attempted. |
| succeeded/executed | The runtime has explicit evidence that the provider/tool completed successfully. |
| blocked | Governance or public-demo policy prevented execution after a real request. |

Provider selected is not provider attempted. Provider attempted is not provider succeeded. Tool selected/planned is not tool invoked. Tool invoked/executed requires actual attempt/execution evidence or an explicit governance block on a real tool request.

## Local and matcher lanes

Matcher shortcuts, rule-based intent classification, direct local responses, and compatibility execution are valid runtime lanes. They are not failures by themselves, but they are not full cognitive execution. Public diagnostics should keep them visible so contributors do not mistake a helpful local answer for provider/tool-backed cognition.

## Debugging guidance

When filing a classification bug, include:

- the prompt
- `runtime_mode`
- `runtime_reason`
- `semantic_runtime_lane`
- `execution_runtime_lane`
- `execution_path_used`
- `fallback_triggered`
- `compatibility_execution_active`
- `provider_actual`
- `execution_provenance`

# Runtime Modes

This document defines the canonical runtime modes used by Omni public debugging and runtime inspection.

The goal is to keep `runtime_mode` tied to evidence, not to generic transport success.

## Canonical modes

| Mode | Meaning | Required evidence | Common causes | Contributor notes |
| --- | --- | --- | --- | --- |
| `FULL_COGNITIVE_RUNTIME` | A real action-backed runtime completed with a complete cognitive chain. | `semantic_runtime_lane=true_action_execution`, `execution_runtime_lane=true_action_execution`, `compatibility_execution_active=false`, `cognitive_chain=COMPLETE` | Node emitted `execution_request.actions` and Python executed them successfully. | This is the strongest healthy path currently available. |
| `PARTIAL_COGNITIVE_RUNTIME` | A non-fallback result exists, but the evidence does not justify a full runtime claim. | Non-empty response, no explicit fallback/provider failure, incomplete chain or bridge-only path. | Bridge execution request, partial planning, incomplete structured execution. | Do not confuse this with true action execution. |
| `NODE_EXECUTION_SUCCESS` | Node succeeded with a real action-backed path, but the turn did not meet the stricter full-runtime gate. | `semantic_runtime_lane=true_action_execution`, `execution_path_used=node_execution`, `transport_status=success` | Action path executed, but planning/reasoning/chain completeness remained partial. | Stronger than partial, weaker than full. |
| `LOCAL_TOOL_SUCCESS` | A local tool branch executed successfully without degrading to compatibility fallback. | `execution_runtime_lane=local_tool_execution` or Node hint `node_local_tool_run` plus success evidence. | Local tool execution path from Node authority or explicit local tool branch. | This is a real execution path, but it is distinct from Node action graph execution. |
| `MATCHER_SHORTCUT` | A matcher answered the turn without real execution. | `semantic_runtime_lane=matcher_shortcut` or explicit Node matcher hint. | Greeting and conversational shortcut matchers. | A valid response can still be operationally weak. |
| `DIRECT_LOCAL_RESPONSE` | A local direct response was returned without tool/action execution. | `semantic_runtime_lane=local_direct_response` | Memory reply, no-tool local answer, direct conversational path. | This is not a cognitive execution success. |
| `SAFE_FALLBACK` | The runtime intentionally returned the safe fallback path. | `fallback_triggered=true` or safe degraded lane without explicit Node failure evidence. | Governance block, compatibility fallback, empty operational path. | Safe fallback is truthful; it should not be hidden as success. |
| `NODE_FAILURE` | The Node path failed or returned an unusable payload. | Node failure reason such as `timeout`, `subprocess_exception`, `empty_node_response`, `invalid_json` | Broken subprocess, empty Node payload, invalid structured response. | This is stronger than generic fallback because the Node failure is explicit. |
| `PROVIDER_FAILURE` | A provider-backed path failed and the failure is explicitly evidenced. | `execution_provenance.provider_failed=true` or `failure_class` indicates provider failure | Provider timeout, provider unavailable, upstream model failure. | Do not infer this from text alone. |
| `COMPATIBILITY_EXECUTION` | The turn completed through the compatibility path. Supported, but not the long-term happy path. | `compatibility_execution_active=true` or `execution_runtime_lane=compatibility_execution` | Strategy dispatch downgraded to compatibility runtime path. | This should remain visible in reports and bug filings. |

## Evidence hierarchy

Omni now resolves runtime truth in this order:

1. explicit failure evidence
2. fallback flag
3. compatibility execution flag
4. execution path used
5. Node hint and execution provenance
6. provider information
7. response content only as a last resort

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

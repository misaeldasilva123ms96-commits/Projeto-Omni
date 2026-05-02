# Runtime Truth Contract

## Runtime Modes

Public runtime truth may report:

- `FULL_COGNITIVE_RUNTIME`
- `PARTIAL_COGNITIVE`
- `MATCHER_SHORTCUT`
- `RULE_BASED_INTENT`
- `SAFE_FALLBACK`
- `NODE_FALLBACK`
- `PROVIDER_UNAVAILABLE`
- `TOOL_BLOCKED`
- `TOOL_EXECUTED`
- `MEMORY_ONLY_RESPONSE`

## Matcher Labeling

Local matchers are labeled as `MATCHER_SHORTCUT`. Matcher responses must set provider attempt/success and tool invocation/execution to false. Matchers may be enabled, labeled-only, or disabled by feature flag, but the default public-demo mode is enabled and labeled.

## Fallback Labeling

Any fallback or degraded path must set `fallback_triggered=true` where a fallback response is used and must not claim full cognitive runtime success. Node empty responses and service failures use degraded public modes and public error taxonomy.

## Provider Tracking

Runtime truth tracks provider attempt and success separately. Provider unavailable or failed execution must report provider success as false and must not be promoted to `FULL_COGNITIVE_RUNTIME`.

## Tool Tracking

Runtime truth tracks tool invocation and execution separately. Governance blocks and shell policy blocks must report `tool_invoked=true` when a tool was requested, `tool_executed=false`, and `tool_status=blocked`.

## Classifier Source And Mode

Phase 12 adds safe classifier observability:

- `intent_source`
- `classifier_version`
- `classifier_mode`
- `classifier_provider_attempted`
- `classifier_provider_succeeded`

Regex remains the default classifier. Embedding, LLM, and hybrid modes are feature-flagged and do not execute tools from classifier output.

## Service And Circuit Breaker Behavior

Subprocess mode remains default. Python/Node service modes are opt-in. Rust Python service failures use timeout/error taxonomy, circuit breaker state, optional fallback metadata, and degraded runtime truth. Service fallback to subprocess is explicit and cannot claim full runtime success.

## Public-Safe Fields

Allowed public diagnostic fields include runtime mode/reason, intent/source, classifier mode/version, fallback status, provider/tool status, latency, request id, public warnings, public error code/message, internal redaction flag, and public summary.

## Never Full Runtime

The following must never be labeled `FULL_COGNITIVE_RUNTIME`:

- matcher shortcut responses
- safe fallback responses
- node fallback or empty response
- provider unavailable or failed response
- tool blocked response
- governance blocked response
- memory-only answer without provider success
- service failure with fallback
- low-confidence classifier result
- payload without usable execution result

# PHASE 2 RUNTIME TRUTH CONTRACT — Projeto Omni

Date: 2026-05-01
Base branch: hardening/learning-redaction-01e
Base commit: f7fc535e32afa19b8843892f184ad1dcf6bdd108
Working branch: runtime/truth-contract-02

## Scope

Phase 2 adds an explicit runtime truth contract without changing execution architecture, matcher behavior, provider routing, tool execution, security sanitizers, or public raw debug exposure.

## Runtime Truth Paths Inspected

| Area | Path | Finding |
| --- | --- | --- |
| Node decision authority | core/brain/queryEngineAuthority.js | Intent inference, matcher shortcuts, no-tool local responses, bridge execution requests, and local tool result paths are generated here. |
| Execution provenance | core/brain/executionProvenance.js | Existing provider/tool provenance remains intact and is not replaced. |
| Provider router | platform/providers/providerRouter.js | Local heuristic provider is embedded and must not be treated as LLM provider success. |
| Python runtime inspection | backend/python/brain/runtime/observability/cognitive_runtime_inspector.py | Public runtime status is derived from semantic lane, node outcome, provenance, tool diagnostics, fallback state, and memory hit flags. |
| Public payload boundary | backend/python/brain/runtime/observability/public_runtime_payload.py | Public sanitizer must preserve safe runtime truth fields while stripping raw internals. |

## Intent Wrapper Path

`core/brain/queryEngineAuthority.js` now exposes `inferIntentWithSource(message)` without changing the existing `inferIntent(message)` signature.

Returned fields:

- `intent`
- `intent_source: rule_based`
- `confidence: 0.7`
- `classifier_version: regex_v1`

## Modes Added / Normalized

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

## Truth Rules Implemented

- Greeting/local matcher payloads are labeled `MATCHER_SHORTCUT`.
- Matcher truth forces `llm_provider_attempted=false` and `tool_invoked=false`.
- Regex intent is labeled `intent_source=rule_based` and `classifier_version=regex_v1`.
- Provider failure/no provider availability is represented as `PROVIDER_UNAVAILABLE`, never full runtime.
- Tool policy denial is represented as `TOOL_BLOCKED` with `tool_executed=false`.
- Successful tool/action diagnostics are represented as `TOOL_EXECUTED` with `tool_executed=true`.
- Fallback truth cannot remain `FULL_COGNITIVE_RUNTIME`; fallback becomes `SAFE_FALLBACK`.
- Node empty/unusable response is represented as `NODE_FALLBACK`.
- Node local/direct payload without `execution_request` is represented as `RULE_BASED_INTENT`, not full runtime.
- Direct memory hit is represented as `MEMORY_ONLY_RESPONSE` and does not claim provider success.

## Public Payload Interaction

`build_public_cognitive_runtime_inspection(...)` preserves safe `runtime_truth` fields and derived public fields:

- intent/source/classifier version
- matcher/provider/tool/fallback/node booleans
- public summaries
- runtime mode/reason

The existing recursive sanitizer still removes raw internals such as stack traces, stdout/stderr, commands, args, env, secrets, provider raw responses, execution requests, raw tool results, and memory content.

## Tests Run / Results

Narrow tests:

- `node tests/runtime/runtimeTruthContract.test.mjs` — passed
- `python -m pytest -q tests/runtime/observability/test_runtime_truth_contract.py` — passed after correcting the test assertion to check keys rather than substrings inside safe reason text
- `python -m pytest -q tests/runtime/observability/test_public_runtime_payload.py` — passed
- `python -m pytest -q tests/runtime/observability/test_cognitive_runtime_inspector.py` — passed

Broad validation results are recorded in the final Phase 2 report.

## Known Limitations

- Phase 2 does not introduce a learned classifier or alter `inferIntent`; the source remains deterministic regex/rule-based.
- Provider truth depends on the existing provenance/diagnostic fields supplied by provider execution paths.
- Full end-to-end Render behavior is not validated by this phase unless separately deployed.

## Rollback

Rollback command:

```bash
git revert <phase-2-commit>
```

## Gate 2 Status

PASSED if all required validations complete or any broad-suite failures are documented as inherited/unrelated with evidence.

## No Merge Into Main

Confirmed. This phase is committed only to `runtime/truth-contract-02`.

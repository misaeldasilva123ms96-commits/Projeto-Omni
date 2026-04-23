# Brain Audit Baseline

Date: 2026-04-22
Branch baseline captured on: `audit/brain-runtime-full-review`
Previous working branch at audit start: `feat/cloudflare-pages-deploy`

## Current project phase / status

The repository is not a greenfield runtime. It already contains:

- Python cognitive orchestration with `BrainOrchestrator`
- Rust HTTP transport with `/chat` and `/api/v1/chat`
- Node/JS query engine routing and fallback behavior
- OIL translation, capability routing, execution manifest, strategy dispatch, observability, governance, provenance, memory, and optional LoRA augmentation
- multiple recently-added control-plane and training layers

The architecture is feature-rich, but the baseline evidence shows that "response exists" is not a trustworthy proxy for "healthy cognitive execution".

## Key runtime modules frozen for audit

### HTTP / transport

- `backend/rust/src/main.rs`
- `backend/python/main.py`

### Core decision/runtime

- `backend/python/brain/runtime/orchestrator.py`
- `backend/python/brain/runtime/orchestrator_services/execution_dispatch_service.py`
- `core/brain/queryEngineAuthority.js`
- `js-runner/queryEngineRunner.js`
- `src/queryEngineRunnerAdapter.js`

### Internal language / I/O

- `backend/python/brain/runtime/language/*`

### Memory / context

- `backend/python/brain/runtime/memory/*`
- `backend/python/brain/memory/*`

### Governance / control

- `backend/python/brain/runtime/control/*`

### Observability / provenance

- `backend/python/brain/runtime/observability/*`
- `backend/python/brain/runtime/provenance/*`
- `core/brain/executionProvenance.js`

## Public request / response path baseline

Observed public entrypoints:

- Rust receives `POST /chat`
- Rust also exposes `POST /api/v1/chat`
- both routes are documented in `backend/rust/src/main.rs` as the public execution path

Current transport envelope expectations:

- Rust request body requires `message`
- Python `backend/python/main.py` returns JSON-only stdout
- Python response is sanitized before Rust sees it
- Rust response can include:
  - `response`
  - `session_id`
  - `source`
  - `runtime_session_version`
  - `client_session_id`
  - `matched_commands`
  - `matched_tools`
  - `stop_reason`
  - `usage`
  - `conversation_id`
  - `cognitive_runtime_inspection`
  - `providers`

Important baseline fact:

- `backend/python/main.py` injects `providers = get_available_providers()`, which is an availability list, not proven actual provider selection for the turn.

## Known symptoms at baseline

Evidence-backed symptoms observed in this phase:

1. A simple greeting (`"ola"`) returns a valid response, but the inspection still reports:
   - `runtime_mode = NODE_EXECUTION_SUCCESS`
   - `cognitive_chain = PARTIAL`
   - `final_verdict = HYBRID_UNSTABLE`
   - performance note: `python_reasoning_strategy_then_node_planner_likely_redundant_work`

2. A memory-style question (`"qual e o meu nome?"`) degraded into:
   - `response = NODE_FALLBACK_RESPONSE`
   - `last_runtime_reason = subprocess_exception`
   - `final_verdict = DEGRADED_SYSTEM`

3. A runtime-explanation prompt (`"explique o fluxo do runtime Omni"`) degraded into:
   - `response = NODE_FALLBACK_RESPONSE`
   - `last_runtime_reason = timeout`
   - `duration_ms = 123345`

4. The system can declare strategy dispatch success while still ending in degraded Node fallback:
   - `strategy_dispatch_applied = true`
   - `executor_used = direct_response_executor`
   - `strategy_execution_status = success`
   - yet final user-visible response still degraded to Node fallback in two representative prompts

5. Node contains explicit conversational matchers and a global conversational fallback before the deeper runtime path:
   - `core/brain/queryEngineAuthority.js`

6. Python `main.py` sanitizes operational-looking payloads into a generic Python fallback response, which is correct for safety but can hide upstream defects from the public envelope.

## Baseline evidence table

| Prompt | Expected behavior | Actual behavior | Runtime mode | Provider / provenance visibility | Notes |
| --- | --- | --- | --- | --- | --- |
| `ola` | low-latency direct greeting, ideally without heavy degraded path risk | `"Olá! Sou o Omni. Como posso te ajudar hoje?"` | `NODE_EXECUTION_SUCCESS` with `final_verdict = HYBRID_UNSTABLE` | public Python envelope exposed `providers = ["openai","anthropic","groq","gemini","deepseek"]`; no proven actual selected provider surfaced | Response is correct, but path is partially cognitive and expensive (`duration_ms` observed at 34s and 63s in separate runs). |
| `meu nome e Misael` -> `qual e o meu nome?` | memory should persist and answer with recalled name | degraded Node fallback response | `NODE_FALLBACK` | no actual provider selected; inspection preserved fallback reason | Memory-oriented turn failed despite memory-heavy architecture. Baseline does not prove memory is functionally helping. |
| `explique o fluxo do runtime Omni` | analytical explanation of current runtime flow | degraded Node fallback response | `NODE_FALLBACK` | no actual provider selected; inspection preserved fallback reason `timeout` | High-value runtime question degraded after ~123s. |
| Python public stdin envelope with `{"message":"ola",...}` | valid JSON-only user-safe envelope | valid JSON envelope with `response`, `stop_reason`, `cognitive_runtime_inspection`, `providers` | `NODE_EXECUTION_SUCCESS` / `HYBRID_UNSTABLE` | only provider availability list surfaced | Public envelope works, but trustworthiness of "providers" and runtime success needs deeper audit. |

## Observed fallback / degraded behaviors

Baseline observed directly:

- `NODE_FALLBACK`
- `HYBRID_UNSTABLE`
- public Python degraded fallback envelope in `backend/python/main.py`

Observed by code inspection and tests:

- matcher/conversational shortcut path in `core/brain/queryEngineAuthority.js`
- `SAFE_FALLBACK`, `MATCHER_SHORTCUT`, `ERROR_DEGRADED`, `PARTIAL_COGNITIVE`, `FULL_COGNITIVE_RUNTIME` classifications in `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`

## Relevant existing tests at baseline

Tests that currently anchor behavior:

- `tests/smoke/test_orchestrator.py`
- `tests/runtime/observability/test_cognitive_runtime_inspector.py`
- `tests/runtime/test_strategy_execution_integration.py`
- `tests/smoke/test_engine_selection_observability.py`
- `tests/runtime/control/*`
- `tests/runtime/language/*`
- `tests/runtime/memory/*`

Important baseline interpretation:

- The current test suite proves many contracts and classifications.
- It does not by itself prove that the dominant user-facing path is a true, stable, non-degraded cognitive flow.

## Known runtime inspection fields at baseline

Observed in live execution:

- `runtime_mode`
- `cognitive_chain`
- `cognitive_chain_steps`
- `source_of_truth`
- `memory_usage`
- `detected_failures`
- `performance_notes`
- `evolution_status`
- `evolution_detail`
- `final_verdict`
- `signals.last_runtime_mode`
- `signals.last_runtime_reason`
- `signals.reasoning_validation`
- `signals.learning_execution_path`
- `signals.duration_ms`
- `signals.ambiguity_detected`
- `signals.ambiguity_score`
- `signals.ranking_applied`
- `signals.ranked_strategy`
- `signals.executor_used`
- `signals.strategy_execution_status`
- `signals.manifest_driven_execution`
- `signals.response_synthesis_mode`

## Known provider / provenance behavior at baseline

Evidence available in this phase:

- Rust and Python public envelopes support `providers`.
- Python currently surfaces available providers, not necessarily actual turn-level provider selection.
- Provenance modules exist in both Python and Node, but turn-level end-to-end integrity has not yet been proven in this phase.

## Suspected high-risk modules

### Tier 1

- `backend/python/brain/runtime/orchestrator.py`
  - central coordination point with very high dependency fan-in
  - likely overloaded and difficult to reason about locally

- `core/brain/queryEngineAuthority.js`
  - contains direct conversational matchers and global fallback behavior that may shortcut or mask deeper runtime behavior

- `js-runner/queryEngineRunner.js`
  - carries payload parsing, candidate loading, runtime mode selection, and degraded node fallback behavior in one boundary module

### Tier 2

- `backend/python/main.py`
  - safety sanitizer is valid, but may hide upstream structural faults behind a transport-safe fallback

- `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`
  - conservative and useful, but it is downstream truth-classification logic and may be reporting an already degraded reality rather than preventing it

- `backend/rust/src/main.rs`
  - public envelope is additive and broad; provider and runtime inspection truthfulness must be audited at the boundary level later

## Baseline conclusion

The current Omni brain cannot be assumed healthy based on successful responses alone.

Baseline evidence already shows:

- partially cognitive but expensive greeting flow
- degraded failure on memory-oriented prompt
- degraded failure on runtime-explanation prompt
- mismatch between strategy-dispatch "success" and user-visible Node fallback

This baseline is sufficient to detect regressions or improvements in later audit phases.

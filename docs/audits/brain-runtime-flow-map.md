# Brain Runtime Flow Map

Date: 2026-04-22
Phase: B — Real Cognitive Flow Validation
Status: real flow documented; no remediation applied

## Real request-to-response path

### Public HTTP path

1. Rust receives `POST /chat` or `POST /api/v1/chat`
   - module: `backend/rust/src/main.rs`
   - functions: `chat`, `public_v1_chat`

2. Rust serializes a JSON stdin body for Python
   - function: `build_python_stdin_json`

3. Rust spawns Python entrypoint
   - function: `call_python`
   - target: `backend/python/main.py`

4. Python entrypoint resolves message / bridge metadata and instantiates orchestrator
   - module: `backend/python/main.py`
   - functions: `resolve_entry_message`, `apply_bridge_env`, `main`

5. Python invokes the cognitive runtime
   - module: `backend/python/brain/runtime/orchestrator.py`
   - function: `BrainOrchestrator.run`

6. Python orchestrator performs pre-execution cognitive stages
   - OIL/input normalization
   - memory context build
   - strategy adaptation
   - reasoning trace
   - control layer evaluation
   - execution manifest build
   - ambiguity detection
   - decision ranking

7. Python dispatches strategy execution
   - function: `_dispatch_strategy_execution`
   - module: `backend/python/brain/runtime/execution/strategy_dispatcher.py`

8. Current executors mostly reuse the compatibility runtime path
   - `direct_response_executor`
   - `multi_step_reasoning_executor`
   - `tool_assisted_executor`
   - all observed routes in this phase ultimately relied on `compat_execute()`

9. Compatibility path continues into swarm / Node-oriented execution
   - function: `_execute_strategy_compatible_path`
   - then `self.swarm_orchestrator.run(...)`
   - then Node boundary handling

10. Node-side query authority decides the visible behavior
   - `js-runner/queryEngineRunner.js`
   - `src/queryEngineRunnerAdapter.js`
   - `core/brain/queryEngineAuthority.js`

11. Python emits cognitive runtime inspection
   - module: `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`

12. Python sanitizes public output
   - module: `backend/python/main.py`
   - function: `sanitize_for_user`

13. Rust parses Python JSON and shapes final public response
   - function: `extract_chat_from_python_output`

## Stage-by-stage map

| Stage | Input shape | Output shape | Responsible module/function | Failure modes | Fallback modes | Observability evidence | Tests seen |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HTTP entry | `{message,...}` JSON | validated request | `backend/rust/src/main.rs::chat`, `public_v1_chat` | empty message invalid request | immediate 400-style invalid request path | Rust logs | Rust tests in `main.rs` |
| Rust -> Python stdin | message + client/session metadata | JSON bytes | `build_python_stdin_json` | bad serialization unlikely | minimal fallback body | Rust source evidence | Rust tests around python output parsing |
| Python entry | stdin/argv message | orchestrator invocation | `backend/python/main.py::main` | unhandled exception | `USER_FALLBACK_RESPONSE` with technical inspection | JSON stdout | implicit through smoke tests |
| Input interpretation | raw message | OIL request + normalized input | `normalize_input_to_oil_request`, `translate_to_oil_projection`, reasoning engine | reasoning exception | fallback reasoning payload | runtime events + final inspection | language tests |
| Memory/context | message + session | memory context payload | `unified_memory.build_reasoning_context` | memory build failure | zeroed memory context payload | runtime memory trace event | memory tests |
| Governance/control | message + metadata | routing decision + control result | `_evaluate_control_layer` | control block | safe fallback | control events | control tests |
| Runtime upgrade | routing + OIL | manifest + oil summary | `_build_runtime_upgrade_artifacts` | manifest build exception | runtime upgrade fallback | `runtime_oil`, `runtime_manifest` | manifest tests |
| Decision ranking | routing + manifest | effective routing decision | `_apply_decision_ranking` | ranking exception | deterministic routing retained | ranking events | learning/ranking tests |
| Strategy dispatch | selected strategy + manifest | strategy execution result | `_dispatch_strategy_execution`, `StrategyDispatcher.dispatch` | dispatcher exception | compatibility fallback / safe fallback | strategy events | strategy dispatcher tests |
| Compatibility execution | selected strategy + compat callback | swarm/node result | `_execute_strategy_compatible_path` | downstream node/subprocess failures | node fallback or local direct response | final inspection + runtime events | strategy integration test |
| Node authority | execution request or local conversation path | response + hints/provenance | `core/brain/queryEngineAuthority.js::submitMessage` | internal execution issues | conversational matcher, no-tool-local, python executor bridge, global fallback | direct Node evidence in this phase | JS runtime tests |
| Python sanitization | raw internal result | public-safe dict | `backend/python/main.py::sanitize_for_user` | malformed internal payload | degraded python fallback | public JSON output | indirect |
| Rust final parse | Python stdout string | `ChatResponse` | `extract_chat_from_python_output` | empty stdout, invalid JSON | Rust-side degraded fallback | `cognitive_runtime_inspection` may be injected | Rust tests |

## Runtime path classification model

This phase uses the following operational buckets:

### 1. True cognitive path

Definition:
- `runtime_mode = FULL_COGNITIVE_RUNTIME`
- `cognitive_chain = COMPLETE`
- tool usage / execution graph actually exercised
- user-visible result is not a shortcut or degraded wrapper

Observed in this phase:
- none

### 2. Matcher shortcut

Definition:
- response is produced by Node-side direct conversational matcher logic
- underlying Node authority marks:
  - `cognitive_runtime_hint.lane = matcher_shortcut`
  - `execution_mode = matcher_shortcut`

Observed directly in this phase:
- `ola`
- `o que voce faz?`

Source evidence:
- direct Node authority invocation
- code path in `core/brain/queryEngineAuthority.js`

### 3. Local direct response

Definition:
- no real tool execution occurs
- Node authority returns `no_tool_local` or equivalent direct answer path
- user receives a structured or memory-informed local answer

Observed directly in this phase:
- `qual e o meu nome?` when executed directly against Node authority

### 4. Safe/degraded fallback

Definition:
- system explicitly reports degraded mode / fallback
- path truthfully signals that execution failed or was blocked

Observed live in this audit program:
- Phase A prompt: `explique o fluxo do runtime Omni` returned `NODE_FALLBACK`
- Phase A memory recall case also hit `NODE_FALLBACK`

Observed by code / boundary:
- Python `USER_FALLBACK_RESPONSE`
- Rust `PYTHON_FALLBACK_RESPONSE`
- Node `USER_FALLBACK_RESPONSE`

### 5. Node failure masked as response

Definition:
- user receives a coherent response string
- internal markers say strategy dispatch/execution succeeded
- but actual path is only partial, shortcut, or bridge-preparation rather than a completed cognitive execution

Observed directly in this phase:
- greeting
- generic conversational
- runtime explanation
- tool-capable intent
- degraded/failure-style tool request

This is the dominant current pattern.

## Truth table for representative prompts

### Notes on entry path

For all Python runtime prompts below, the common entry path was:

- Rust-equivalent public contract
- `backend/python/main.py`
- `BrainOrchestrator.run`
- `_build_runtime_upgrade_artifacts`
- `_apply_decision_ranking`
- `_dispatch_strategy_execution`
- compatibility runtime path
- Node-side authority behavior
- Python cognitive runtime inspection

The distinction is not the entry path; it is where the path actually collapses into shortcut, local direct response, bridge envelope, or degraded fallback.

| Category | Prompt | Responsible modules/functions | Executor used | runtime_mode | cognitive_chain | final_verdict | strategy_dispatch_applied | strategy_execution_status | last_runtime_reason | Did Node actually execute successfully? | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| greeting | `ola` | `main.py -> BrainOrchestrator.run -> _dispatch_strategy_execution -> direct_response_executor -> compat path -> QueryEngineAuthority.submitMessage` | `direct_response_executor` | `NODE_EXECUTION_SUCCESS` | `PARTIAL` | `HYBRID_UNSTABLE` | `true` | `success` | `direct_node_response` | yes, but as Node matcher shortcut | matcher shortcut masked as node success |
| memory recall | `qual e o meu nome?` | same Python path; underlying Node evidence shows `QueryEngineAuthority.submitMessage` can return `no_tool_local` | `direct_response_executor` | `NODE_EXECUTION_SUCCESS` | `PARTIAL` | `HYBRID_UNSTABLE` | `true` | `success` | `direct_node_response` | yes, but as local/no-tool path rather than true cognitive completion | local direct response masked as node success |
| runtime explanation | `explique o fluxo do runtime Omni` | same Python path; Node returns local explanation wrapper | `direct_response_executor` | `NODE_EXECUTION_SUCCESS` | `PARTIAL` | `HYBRID_UNSTABLE` | `true` | `success` | `direct_node_response` | yes, but without tool usage or full execution graph completion | node failure masked as response / partial local completion |
| generic conversational | `o que e uma api?` | same Python path; direct Node authority proves conversational matcher exists | `direct_response_executor` | `NODE_EXECUTION_SUCCESS` | `PARTIAL` | `HYBRID_UNSTABLE` | `true` | `success` | `direct_node_response` | yes, but as matcher shortcut | matcher shortcut masked as node success |
| tool-capable intent | `analise o arquivo package.json` | same Python path; Node authority returns `python_executor_bridge` wrapper with execution request payload | `direct_response_executor` | `NODE_EXECUTION_SUCCESS` | `PARTIAL` | `HYBRID_UNSTABLE` | `true` | `success` | `direct_node_response` | yes, but only as bridge-preparation envelope; not a completed tool result | node failure masked as response / bridge-only completion |
| degraded/failure-triggering intent | `leia o arquivo package.json e explique os riscos de arquitetura` | Python path ranked to `MULTI_STEP_REASONING`; executor still used compat path; Node returned bridge wrapper instead of completed analysis | `multi_step_reasoning_executor` | `NODE_EXECUTION_SUCCESS` | `PARTIAL` | `HYBRID_UNSTABLE` | `true` | `success` | `direct_node_response` | yes, but only as bridge-preparation envelope | node failure masked as response / partial cognitive path |

## Direct Node authority evidence captured in this phase

These calls were executed directly against `core/brain/queryEngineAuthority.js::submitMessage` to determine what the Node layer is really doing before Python classification flattens it.

### Greeting

Prompt:
- `ola`

Direct Node result:
- `cognitive_runtime_hint.lane = matcher_shortcut`
- `detail = regex_greeting`
- provenance `execution_mode = matcher_shortcut`

### Generic conversational

Prompt:
- `o que voce faz?`

Direct Node result:
- `cognitive_runtime_hint.lane = matcher_shortcut`
- `detail = conversational_matcher`
- provenance `execution_mode = matcher_shortcut`

### Memory recall

Prompt:
- `qual e o meu nome?`

Direct Node result:
- `cognitive_runtime_hint.lane = no_tool_local`
- `detail = all_actions_tool_none`
- provenance `execution_mode = no_tool_local`

### Tool-capable intent

Prompt:
- `analise o arquivo package.json`

Direct Node result:
- `cognitive_runtime_hint.lane = node_execution_graph`
- `detail = python_executor_bridge`
- returns `execution_request` plan payload instead of a completed file analysis

## Mismatch analysis

### Mismatch 1: `NODE_EXECUTION_SUCCESS` does not mean true cognitive completion

Observed repeatedly:
- greeting
- generic conversational
- memory recall
- runtime explanation
- tool-capable intent

Why this is a mismatch:
- the inspection says Node execution succeeded
- but the underlying Node authority may actually be returning:
  - `matcher_shortcut`
  - `no_tool_local`
  - `python_executor_bridge`
- none of those are equivalent to a full cognitive completion

### Mismatch 2: `strategy_dispatch_applied = true` and `strategy_execution_status = success` do not imply healthy user-visible completion

Observed repeatedly across all representative prompts.

Why this is a mismatch:
- the dispatcher/executor layer can report success while only calling the compatibility runtime path
- the compatibility path can still collapse into:
  - conversational matcher
  - local no-tool response
  - bridge-preparation envelope
  - degraded fallback in other runs

### Mismatch 3: tool-capable prompts can end in bridge wrappers instead of execution

Observed for:
- `analise o arquivo package.json`
- `leia o arquivo package.json e explique os riscos de arquitetura`

Why this is a mismatch:
- user-visible output suggests a plan was prepared and forwarded
- but no completed tool-backed analysis is returned
- inspection still records `NODE_EXECUTION_SUCCESS`

### Mismatch 4: matcher hints are not preserved into final runtime classification

Observed by comparing:
- direct Node authority output for `ola` and `o que voce faz?`
- Python runtime inspection for those same prompts

Direct Node says:
- `matcher_shortcut`

Python final inspection says:
- `NODE_EXECUTION_SUCCESS`
- `source_of_truth = Node`
- no `node_cognitive_hint`

This indicates loss or flattening of shortcut provenance across the Python/Node boundary or later orchestration layer.

### Mismatch 5: a valid public envelope can hide degraded operational truth

Observed at two levels:

- current phase:
  - public-safe responses exist even when the path is only partial or bridge-only
- previous baseline evidence from the same audit program:
  - some prompts ended in explicit `NODE_FALLBACK`

This proves that HTTP/JSON success is not equivalent to functional cognitive success.

## Happy path vs degraded path vs shortcut path

### Happy path actually observed

Strictly speaking:
- no fully trustworthy `true cognitive path` was observed in this phase

### Partial cognitive path observed

Observed dominant pattern:
- Python orchestration, ranking, and strategy dispatch run
- compatibility path executes
- Node returns a coherent string
- tool usage/simulation remains false
- final verdict remains `HYBRID_UNSTABLE`

### Matcher / shortcut path observed

Observed directly in Node:
- `ola`
- `o que voce faz?`

### Local direct response path observed

Observed directly in Node:
- `qual e o meu nome?`

### Safe / degraded fallback observed

Observed earlier in this audit program with live runtime prompts:
- `NODE_FALLBACK` on memory/runtime explanation paths

### Node failure masked as response observed

Observed in this phase for bridge-oriented prompts and local wrapper outputs where:
- visible text exists
- internal status says success
- but there is no completed deep cognitive/tool-backed execution

## Flow validation result

The real execution graph is now clear enough to separate:

- public transport success
- strategy dispatch success
- compatibility runtime execution
- underlying Node shortcut/local/bridge behaviors
- degraded fallback behavior

The current Omni runtime does not yet justify treating `NODE_EXECUTION_SUCCESS` as equivalent to "healthy cognitive completion".

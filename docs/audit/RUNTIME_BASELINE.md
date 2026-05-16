# Omni Runtime Baseline Audit

Audit date: 2026-05-14  
Audited branch: `chore/github-agent-profiles`  
Audited commit: `7b946dce264737787bc5fbf5bb1b7fd05ce7ac4a`  
Mode: static/read-only source audit plus report creation only. No source code, config, lockfile, test, env, or runtime implementation files were modified.

## 1. Executive summary

The current chat request path proven by source is:

`Rust/Axum /chat or /api/v1/chat -> backend/python/main.py subprocess by default -> BrainOrchestrator -> optional Node subprocess -> js-runner/queryEngineRunner.js -> src/queryEngineRunnerAdapter.js -> core/brain/fusionBrain.js -> core/brain/queryEngineAuthority.js -> local matcher/local guidance/tool bridge/fallback -> Python public sanitizer -> Rust response`.

Key conclusions:

- Rust HTTP chat entrypoints are real in `backend/rust/src/main.rs` at `chat` and `public_v1_chat`.
- Python public entrypoint is real in `backend/python/main.py`; it instantiates `BrainOrchestrator` and sanitizes the result before JSON stdout.
- Node QueryEngine path is real, but the active adapter is `src/queryEngineRunnerAdapter.js`, which delegates to `core/brain/fusionBrain.js`, which delegates to `QueryEngineAuthority`.
- In this audited branch, no real remote LLM provider execution module was found. `platform/providers/remoteProviderExecutor.js` is absent. `providerRouter.js` selects/configures providers, but static evidence shows no remote HTTP provider call in the QueryEngineAuthority path.
- Generic responses originate from local matchers, structured local guidance, safe fallback strings, or Node/Python/Rust bridge fallback wrappers.
- Runtime truth is stronger than a plain HTTP/JSON success check, but the Node authority can still set `llmProviderAttempted` from provider selection/configuration rather than from a proven remote HTTP call. Python inspection is more conservative when it can use diagnostics/provenance, but its accuracy depends on upstream evidence quality.
- The Python swarm agents are real classes and are called from the compatibility/swarm path, but they are deterministic/local orchestration components, not independent remote LLM agents.

Top blocking risks:

1. Provider selection can be mistaken for provider execution in parts of the Node truth/provenance path.
2. Default runtime writes local state (`memory`, transcripts, logs, strategy files) during a normal chat turn, so deployment is stateful unless volumes and retention are explicit.
3. Several state files are read/modify/write without cross-process locking or atomic replace, risking corruption under concurrent requests.

## 2. Confirmed file map

| Logical target | Confirmed path | Evidence |
|---|---|---|
| Rust HTTP entrypoint | `backend/rust/src/main.rs` | Routes include `/api/v1/chat` and `/chat` at lines 493-494; handlers at lines 1839 and 1884. |
| Rust Python subprocess bridge | `backend/rust/src/main.rs` | `build_python_stdin_json` line 2195; `call_python` line 2646; `call_python_subprocess` line 2671. |
| Python public entrypoint | `backend/python/main.py` | `build_public_chat_payload` line 249; `main` line 329. |
| Python BrainOrchestrator/runtime | `backend/python/brain/runtime/orchestrator.py` | `class BrainOrchestrator` line 258; `run` line 507. |
| Python Node subprocess transport | `backend/python/brain/runtime/node_transport.py` | `run_node_subprocess` line 75. |
| Node runner | `js-runner/queryEngineRunner.js` | `main` line 671; candidate loading line 411. |
| Node adapter | `src/queryEngineRunnerAdapter.js` | Exports `runQueryEngine` from `core/brain/fusionBrain.js`. |
| Node QueryEngine authority | `core/brain/queryEngineAuthority.js` | `class QueryEngineAuthority` line 624; `submitMessage` line 630. |
| Provider router | `platform/providers/providerRouter.js` | `getAvailableProviders` line 21; `chooseProvider` line 150. |
| Python provider registry | `backend/python/config/provider_registry.py` | `get_available_providers` line 18; `describe_provider_diagnostics` line 35. |
| Provider secrets forwarding | `backend/python/config/secrets_manager.py` | `_mapping` lines 24-32; `merge_provider_credentials` line 118. |
| Public payload sanitizer | `backend/python/brain/runtime/observability/public_runtime_payload.py` | Imported by `backend/python/main.py` lines 11-16 and used line 326. |
| Runtime truth inspector | `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py` | `build_cognitive_runtime_inspection` line 261; `runtime_truth` construction line 688. |
| Runtime lane classifier | `backend/python/brain/runtime/observability/runtime_lane_classifier.py` | `normalize_node_outcome` line 51; `interpret_node_payload` line 132; `classify_runtime_lane` line 260. |
| Swarm orchestrator | `backend/python/brain/swarm/swarm_orchestrator.py` | `SwarmOrchestrator.run` line 23. |
| Swarm agents | `backend/python/brain/swarm/*_agent.py` | Router, Planner, Executor, Critic, Memory classes are present. |
| Strategy state | `backend/python/brain/evolution/strategy_updater.py` | `strategy_state.json` and `strategy_log.json` set at lines 44-45. |
| Python transcripts | `backend/python/brain/runtime/transcript_store.py` | Per-session JSONL append in `append_turn`. |
| Node transcripts/audit | `storage/transcripts/transcriptPersistence.js` | `execution-audit.jsonl` and `runtime-transcript.jsonl` append functions. |
| Env examples | `.env.example`, `backend/rust/.env.example`, `frontend/.env.example` | Variable-name discovery only. |

## 3. Actual request flow

1. Rust receives HTTP JSON.
   - `backend/rust/src/main.rs::chat` accepts `/chat`.
   - `backend/rust/src/main.rs::public_v1_chat` accepts `/api/v1/chat`.
   - Both validate content type, body size, rate limit, JSON, message, and optional IDs before invoking Python.

2. Rust builds Python stdin JSON.
   - `build_python_stdin_json` creates:
     - `message`
     - `runtime_session_version`
     - `request_source: rust_boundary`
     - optional `client_session_id`
     - optional `request_id`
     - optional `client_context`

3. Rust starts Python.
   - Default mode calls `call_python_subprocess`.
   - Command is `PYTHON_BIN`/default `python` plus `python_entry`, resolved from `backend/python/main.py`.
   - Stdin is JSON bytes; stdout and stderr are captured.
   - Timeout is `state.python_timeout_ms`.
   - Python stdout must be JSON parseable; otherwise Rust returns a safe degraded response.

4. Python main normalizes and sanitizes.
   - `backend/python/main.py::main` calls `resolve_entry_message`.
   - `build_public_chat_payload` loads repo `.env` unless CI, applies bridge env, instantiates `BrainOrchestrator`, calls `orchestrator.run`, normalizes the return through `sanitize_for_user`, attaches public cognitive inspection, provider diagnostics, provider list, and finally calls `sanitize_public_runtime_payload`.
   - Python writes exactly one JSON payload to stdout with `ensure_ascii=False`.

5. BrainOrchestrator executes runtime.
   - Loads memory and recent transcript history.
   - Runs memory context, strategy, reasoning, planning, control, policy, coordination, strategy dispatch, optional Node path, optional local tool path, compatibility/swarm path, evaluation, learning, state persistence, transcript persistence, and cognitive runtime inspection.

6. Node path, when selected.
   - `_call_node_query_engine` builds compact JSON payload:
     - `message`
     - `memory`
     - `history`
     - `summary`
     - `capabilities`
     - `session`
   - Python runs `js-runner/queryEngineRunner.js` via `run_node_subprocess`.
   - Node reads JSON from argv/stdin, validates shape, chooses candidate QueryEngine files, and returns a sanitized JSON result.

7. Node QueryEngineAuthority.
   - `src/queryEngineRunnerAdapter.js` exports `runQueryEngine` from `core/brain/fusionBrain.js`.
   - `fusionBrain.js` calls `QueryEngineAuthority.submitMessage`.
   - `submitMessage` may return:
     - matcher shortcut
     - direct local memory response
     - no-tool structured local guidance
     - Python execution bridge request
     - local tool execution result
     - governance-blocked result
     - fallback result

8. Response returns to Python and Rust.
   - Python interprets Node output via `interpret_node_payload`.
   - Python builds `last_cognitive_runtime_inspection`.
   - Python public sanitizer removes internal fields.
   - Rust parses Python stdout and returns HTTP 200 with `ChatResponse` unless Rust-level validation failed.

## 4. Subprocess boundaries

| Boundary | Caller | Callee | Transport | Timeout/error behavior | Sanitization |
|---|---|---|---|---|---|
| Rust -> Python subprocess | `backend/rust/src/main.rs::call_python_subprocess` | `backend/python/main.py` | JSON bytes on stdin; stdout/stderr captured | Timeout/nonzero/empty stdout/invalid JSON become Rust safe fallback with `SAFE_FALLBACK` inspection | Rust parses only public candidate keys; debug logging disabled in public demo |
| Rust -> Python service mode | `backend/rust/src/main.rs::call_python_service` | `/internal/brain/run` | Manual HTTP over TCP | Timeout/service error can fall back to subprocess depending config | Parsed through same Python-output parser |
| Python -> Node subprocess | `backend/python/brain/runtime/orchestrator.py::_call_node_query_engine` | `js-runner/queryEngineRunner.js` | JSON string to subprocess stdin; stdout/stderr captured | `run_node_subprocess` returns reason codes for timeout, nonzero, invalid JSON, empty stdout | Diagnostics include truncated stdout/stderr; public result later sanitized |
| Node runner -> QueryEngine authority | `js-runner/queryEngineRunner.js::tryRunExistingQueryEngineDetailed` | candidate modules, active `src/queryEngineRunnerAdapter.js` | Dynamic import and in-process function call | Candidate import errors are collected; missing result emits Node fallback JSON | `sanitizeForUser` normalizes public response |
| QueryEngine authority -> Rust executor bridge | `core/brain/queryEngineAuthority.js` | `runtime/execution/rustExecutorBridge.js` | In-process JS call to bridge module | Tool failures become step results/errors | Governance and runtime truth wrap result |

## 5. Payload shape at each boundary

Rust -> Python stdin:

```json
{
  "message": "string",
  "runtime_session_version": 1,
  "request_source": "rust_boundary",
  "client_session_id": "optional string",
  "request_id": "optional string",
  "client_context": "optional object"
}
```

Python -> Node stdin:

```json
{
  "message": "string",
  "memory": "object",
  "history": "array",
  "summary": "string",
  "capabilities": "array",
  "session": "object"
}
```

Node public result shape, after runner sanitization:

```json
{
  "response": "string",
  "runtime_truth": "optional object",
  "metadata": "object",
  "execution_request": "optional object",
  "cognitive_runtime_hint": "optional object",
  "error": "optional object"
}
```

Python public response shape:

```json
{
  "response": "string",
  "stop_reason": "python_completed or failure reason",
  "cognitive_runtime_inspection": "public-safe object",
  "provider_diagnostics": "array",
  "providers": "array of configured provider ids",
  "runtime_mode": "optional public mode",
  "runtime_reason": "optional reason",
  "fallback_triggered": "optional boolean"
}
```

Rust HTTP response shape:

```json
{
  "response": "string",
  "session_id": "python-session",
  "source": "python-subprocess or python-service or fallback",
  "runtime_session_version": 1,
  "client_session_id": "optional",
  "stop_reason": "optional",
  "conversation_id": "optional",
  "cognitive_runtime_inspection": "optional",
  "providers": "optional",
  "error": "optional"
}
```

## 6. Runtime truth assessment

Runtime truth is decided in two layers:

- Node layer: `core/brain/queryEngineAuthority.js::buildRuntimeTruth` builds `runtime_truth` for matcher, no-tool local, bridge, and tool paths.
- Python layer: `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py::build_cognitive_runtime_inspection` builds final inspection and a public `runtime_truth` based on lane classification, execution provenance, tool diagnostics, fallback state, provider diagnostics, and node truth.

Assessment by requested label:

| Label | Current evidence | Assessment |
|---|---|---|
| `FULL_COGNITIVE_RUNTIME` | Python inspector only promotes to full when chain is complete, not matcher/fallback, action graph exists, `execution_path_used == node_execution`, and no compatibility execution. | Conservative in Python. UNKNOWN in live behavior without live run. |
| `PARTIAL_COGNITIVE` | Node bridge path and Python default partial branches exist. | Real label; may represent planned/bridge/local reasoning rather than provider-backed cognition. |
| `RULE_BASED_INTENT` | Node `inferIntent` and `classifyIntent` are regex/rule based; no-tool local without memory maps to rule-based intent. | Real and accurately named when preserved. |
| `SAFE_FALLBACK` | Rust, Python, Node, and orchestrator fallback strings and reason codes exist. | Real. Rust/Python fallback wrappers are public-safe. |
| `ERROR` | There is no single top-level runtime truth mode named exactly `ERROR`; errors are represented as `SAFE_FALLBACK`, `NODE_FALLBACK`, `PROVIDER_UNAVAILABLE`, `TOOL_BLOCKED`, or public error codes. | `ERROR` as a generic label is not a confirmed current runtime truth mode. |

Specific answers:

- Is `provider_attempted` set from real evidence? Partially. Python `_explicit_provider_truth` prefers explicit provider diagnostics/provenance/node truth. However, Node `QueryEngineAuthority` sets `llmProviderAttempted = Boolean(provider && provider.kind !== 'embedded')` at provider selection time, before any proven remote provider call. That is selection/config evidence, not network execution evidence.
- Is `provider_succeeded` set from real evidence? Partially. No-tool local explicitly sets provider success false. Tool path can set provider success as `Boolean(llmProviderAttempted && !providerFailed && toolExecuted)`, which ties provider success to tool execution, not to a remote provider completion.
- Can `fallback_triggered` be false when the response is generic? Yes. Local matcher and no-tool local guidance paths can return generic/local responses with `fallbackTriggered: false`.
- Can a generic/rule-based answer be marked as cognitive success? Python runtime truth can label it `RULE_BASED_INTENT` or `MATCHER_SHORTCUT`; however Node/provenance may still include provider selection metadata. Static evidence does not prove generic local answers become `FULL_COGNITIVE_RUNTIME`, but success/outcome components may treat a good local response as successful turn unless training safety gates exclude it.
- Where is `runtime_mode` decided? Node uses `buildRuntimeTruth`; Python uses `build_cognitive_runtime_inspection`; Rust only wraps or preserves Python inspection except bridge failures.
- What evidence does classifier use? Node intent classifier is rule/regex based in `inferIntent` and `classifyIntent`. Python runtime lane classifier uses Node payload shape, `execution_request`, `cognitive_runtime_hint`, `runtime_truth`, provenance, fallback strings, strategy dispatch metadata, and tool diagnostics.

## 7. Provider/model invocation assessment

| Provider/model path | Classification | Evidence |
|---|---|---|
| OpenAI | Config-only in active QueryEngine path | Python secrets mapping supports `OPENAI_API_KEY`; JS router includes OpenAI model default. No remote executor or OpenAI HTTP call found in active QueryEngine path. |
| Anthropic | Config-only in active QueryEngine path | Python secrets mapping supports `ANTHROPIC_API_KEY`; JS router includes Anthropic model default. No active HTTP call found. |
| Groq | Config-only in active QueryEngine path | Python/JS recognize `GROQ_API_KEY` and `GROQ_MODEL`; no active Groq executor found. |
| Gemini | Config-only in active QueryEngine path | Python/JS recognize `GEMINI_API_KEY`; JS default is `gemini-2.0-flash`; no `remoteProviderExecutor.js` file found. |
| DeepSeek | Config-only in active QueryEngine path | Python/JS recognize `DEEPSEEK_API_KEY`; no active executor found. |
| OpenRouter | Documented/local-history only | Search found OpenRouter only in `.aider.chat.history.md`, not active runtime source. |
| Ollama | Config-only/local endpoint metadata | JS router recognizes `OLLAMA_URL` and model, but no active HTTP invocation found. |
| LM Studio/local | UNKNOWN — file not found | No active runtime evidence found for LM Studio. |
| Hermes adapter | UNKNOWN — file not found | No active runtime evidence found for Hermes adapter. |
| Mock/stub provider | Real fallback/local heuristic | `local-heuristic` is always appended by JS provider router and used for matchers/local responses. |

Bottom line: static analysis of the current branch proves provider discovery/routing, not remote provider execution.

## 8. Generic response origin

Generic or local responses can originate from:

- `directConversationalResponse` in `core/brain/queryEngineAuthority.js`, for simple greetings and basic capability questions.
- `CONVERSATIONAL_MATCHERS` plus `resolveDirectConversational`, for local canned responses.
- `directResponseFromMemory`, for simple memory recall.
- `buildStructuredLocalGuidance`, for no-tool local guidance.
- `GLOBAL_CONVERSATIONAL_FALLBACK`, `SAFE_FALLBACK_RESPONSE`, `NODE_FALLBACK_RESPONSE`, `USER_FALLBACK_RESPONSE`, and Rust `PYTHON_FALLBACK_RESPONSE`, for degraded paths.
- `SwarmOrchestrator` local agents, where `ExecutorAgent` and `CriticAgent` produce deterministic local text around the Node response.

No static evidence proves a remote provider/model is called to produce a generic chat response in this audited branch.

## 9. Swarm inventory: real / partial / stub / docs-only / unknown

| Component | Path | Class/function | Status | Called from | Called in runtime? | Tests? | Main limitation |
|---|---|---|---|---|---|---|---|
| Router | `backend/python/brain/swarm/router_agent.py` | `RouterAgent` | real | `SwarmOrchestrator.run` | yes, when compatibility/swarm path runs | yes, `tests/swarm/test_agents.py` | Deterministic keyword routing. |
| Planner | `backend/python/brain/swarm/planner_agent.py` | `PlannerAgent` | real | `SwarmOrchestrator.run` | yes, when compatibility/swarm path runs | yes | Local subtask generator, not LLM planner. |
| Executor | `backend/python/brain/swarm/executor_agent.py` | `ExecutorAgent` | real | `SwarmOrchestrator.run` | yes, when compatibility/swarm path runs | yes | Produces local canned task results; actual Node execution is separate callback. |
| Critic | `backend/python/brain/swarm/critic_agent.py` | `CriticAgent` | real | `SwarmOrchestrator.run` | yes, when compatibility/swarm path runs | yes | Score heuristic only. |
| Memory | `backend/python/brain/swarm/memory_agent.py` | `MemoryAgent` | real | `SwarmOrchestrator.run` | yes, when compatibility/swarm path runs | yes | Summarizes local memory signals; no vector retrieval itself. |
| Swarm orchestrator | `backend/python/brain/swarm/swarm_orchestrator.py` | `SwarmOrchestrator.run` | real | `BrainOrchestrator._execute_strategy_compatible_path` | yes if dispatcher chooses/falls back to compatibility path | yes/partial | Writes bounded `swarm_log.json`; no locking. |
| JS specialist registry | `core/agents/specialistRegistry.js` | registry functions | real/partial | `features/multiagent/delegationLayer.js`, `queryEngineAuthority.js` | yes in Node authority planning/delegation | yes/unknown per registry | Registry/delegation metadata, not separate processes. |
| JS specialist functions | `features/multiagent/specialists/*.js` | planner/reviewer/critic/etc. functions | real/partial | `queryEngineAuthority.js` imports and calls several via `safeSpecialistCall` | yes in Node authority | yes/partial | Mostly deterministic helpers; failures return sanitized fallback. |
| Python `AgentCoordinator` | `backend/python/brain/runtime/coordination/agent_coordinator.py` | `AgentCoordinator` | real/partial | `BrainOrchestrator.run` | yes, coordination payload path | yes | Coordination analysis, not independent agent execution. |
| Python `SpecialistCoordinator` | `backend/python/brain/runtime/specialists/specialist_coordinator.py` | `SpecialistCoordinator` | real/partial | constructed in `BrainOrchestrator.__init__` | UNKNOWN — no direct runtime call confirmed in inspected snippets | yes | Requires more targeted call graph evidence. |
| Strategy executors | `backend/python/brain/runtime/execution/strategy_executors/*.py` | direct/tool/node/multi/fallback executors | real | `StrategyDispatcher` | yes through dispatcher | yes | Dispatch policy determines actual path; may fall back. |

## 10. UTF-8/PT-BR risk points

- Rust -> Python passes JSON bytes; Python emits `json.dumps(..., ensure_ascii=False)`, so PT-BR characters can pass if terminal/process encoding is UTF-8-compatible.
- Python -> Node uses `subprocess.run(..., text=True, encoding="utf-8", errors="replace")`, which explicitly protects decoding but can replace invalid bytes.
- Node reads stdin with `fs.readFileSync(0, 'utf8')`.
- JSON stdout parsing is strict at Rust and Python boundaries; any non-JSON diagnostic printed to stdout can force fallback.
- Some hardcoded fallback strings lack accents (`Nao`, `utilizavel`), but that is cosmetic. The main risk is stdout contamination, not accent handling.

## 11. Local state inventory

| State | Path/source | Write behavior | Risk |
|---|---|---|---|
| Python user memory | `backend/python/memory/user.json`, `preferences.json`, `notes.md`, `learning.json` via `HybridMemory` | `write_text` writes full files | Local user data persists; no atomic replace in shown code. |
| Python transcripts | `backend/python/transcripts/*.jsonl` via `TranscriptStore.append_turn` | append mode JSONL | No rotation/size cap found in shown code. |
| Node runtime memory | `.logs/fusion-runtime/runtime-memory-store.json` via `runtimeMemoryStore.js` | `fs.writeFileSync` full file | No cross-process lock/atomic replace shown. |
| Node audit log | `.logs/fusion-runtime/execution-audit.jsonl` | `appendFileSync` | Unbounded growth. |
| Node runtime transcript | `.logs/fusion-runtime/runtime-transcript.jsonl` | `appendFileSync` | Unbounded growth. |
| Strategy state | `backend/python/brain/evolution/strategy_state.json` | `write_text` full file | No atomic replace/lock in `StrategyUpdater._write_json`. |
| Strategy log | `backend/python/brain/evolution/strategy_log.json` | read/modify/write full file | Race/corruption risk under concurrent writes. |
| Swarm log | `backend/python/brain/runtime/swarm_log.json` | read/modify/write full file, last 50 events | Bounded, but no lock/atomic replace. |
| Run registry | `.logs/fusion-runtime/control/run_registry.json` | separate backend indicates atomic replace in docstring/search | More robust than other state files. |

## 12. .env.example/config portability check

Confirmed env/config files:

- `.env.example`
- `backend/rust/.env.example`
- `frontend/.env.example`
- `Dockerfile.demo`
- `docker-compose.demo.yml`
- `docker-compose.yml`

Findings:

- `.env.example` contains provider variable names for OpenAI, Anthropic, Groq, Gemini, DeepSeek, Codex, and Ollama placeholders. No secret values were reported.
- `backend/rust/.env.example` includes `PYTHON_BIN=python`.
- Docker demo config uses Linux container paths such as `/app`, `/opt/venv/bin/python`, `/home/omni`, and tmpfs mounts for logs/memory/transcripts/sessions/storage.
- No active `.env.example` absolute Windows path like `C:\Users\...` was found in the searched config set.
- Historical docs may contain absolute local Windows paths, but those are in archived reports, not active env examples.
- `build_controlled_os_environ_base` copies only selected OS env plus `OMINI_*`; in this branch it does not copy arbitrary `OMNI_*`, except `JSRuntimeAdapter` explicitly sets `OMNI_AVAILABLE_PROVIDERS`.

## 13. Stateful vs stateless deployment implication

The runtime is stateful by default. A normal chat turn can read/write:

- Python memory files.
- Python transcripts.
- `.logs/fusion-runtime` runtime memory/audit/transcript files.
- strategy/performance/experience/learning stores.
- swarm log when compatibility/swarm path runs.

Container/demo deployment therefore needs writable volumes/tmpfs for those paths or a deliberate stateless mode. Without volume/retention design, state is ephemeral in containers and potentially unbounded on long-running hosts.

## 14. Top 3 critical risks, ranked

1. Provider execution truth ambiguity.
   - Evidence: `QueryEngineAuthority` sets `llmProviderAttempted` from provider selection at lines 721-722; no active remote provider executor file exists.
   - Impact: runtime can imply a provider was attempted when no remote model call happened.
   - Minimal correction: separate provider selected/configured from provider attempted/succeeded and require executor-level evidence for attempted/succeeded.

2. Default chat path mutates local state.
   - Evidence: `HybridMemory.sync_from_store`, `TranscriptStore.append_turn`, `transcriptPersistence.js`, `StrategyUpdater`, and `swarm_log.json` writes.
   - Impact: live smoke tests and production traffic create local artifacts; stateless deployments lose/corrupt context unless volumes are explicit.
   - Minimal correction: document state contract, add retention/rotation, and add a read-only/dry-run smoke mode.

3. Non-atomic/unlocked state writes.
   - Evidence: `StrategyUpdater._write_json`, `SwarmOrchestrator._append_log`, and `runtimeMemoryStore.js::saveRuntimeMemory` use direct full-file writes without visible cross-process lock.
   - Impact: concurrent requests can corrupt JSON or lose updates.
   - Minimal correction: atomic temp-file replace plus per-file lock for full-file JSON state; keep JSONL append for logs plus rotation.

## 15. Minimal safe patch plan, no implementation

1. Provider truth hardening:
   - Add explicit provider execution fields: `provider_selected`, `provider_configured`, `provider_attempted`, `provider_succeeded`, `provider_failure_class`.
   - Ensure `provider_attempted=true` only from the provider executor boundary.
   - Add tests for configured-but-not-called providers.

2. State safety:
   - Add atomic write helpers for JSON state.
   - Add bounded rotation or size caps for transcripts/audit logs.
   - Add deployment docs listing required writable paths.

3. Smoke-test mode:
   - Add a documented read-only/dry-run baseline command that avoids memory/log writes.
   - Add PT-BR UTF-8 smoke tests against that mode.

## 16. Tests that should be added first

1. Runtime truth provider tests:
   - Provider key configured but no executor call -> `llm_provider_attempted=false`, `llm_provider_succeeded=false`.
   - Provider selected for no-tool local guidance -> not provider attempted.
   - Tool execution success without provider HTTP completion -> not provider succeeded.

2. Request-flow contract tests:
   - Rust -> Python -> Node fixture with PT-BR accents and JSON-only stdout.
   - Node stdout contamination -> Python/Rust safe fallback.
   - Python stderr with success -> no public leak.

3. State safety tests:
   - Strategy state write uses atomic replace.
   - Swarm log remains valid JSON after simulated interrupted write.
   - Transcript/audit rotation or cap behavior.

4. Swarm truth tests:
   - Compatibility/swarm path returns `PARTIAL_COGNITIVE` or equivalent, not full runtime unless Node/tool evidence exists.

## 17. Commands run and results

| Command | Result | Notes |
|---|---|---|
| `pwd; git status --short; git branch --show-current; git rev-parse HEAD` | PASS | Confirmed repo path, branch `chore/github-agent-profiles`, commit `7b946d...`; no dirty status lines before report creation. |
| PowerShell recursive `Get-ChildItem` file discovery | TIMEOUT | Timed out at 120s; replaced with `rg --files`. |
| `rg --files -g "*.rs" -g "*.py" -g "*.js" -g "*.ts" ...` | PASS | Mapped source files. |
| `rg --files -g "*.json" -g ".env.example" -g "*.md" ...` | PASS | Mapped docs/config/examples. |
| `rg` searches for runtime terms/providers/swarm/state | PASS | Used targeted static discovery. |
| `Get-Content` targeted source reads | PASS | Read Rust, Python, Node, provider, sanitizer, swarm, state files. |
| Live run | NOT RUN | Skipped because normal Python/Node runtime writes local memory, transcripts, and logs, violating the report-only/no-file-modification constraint. |
| Build/install/test commands | NOT RUN | Prohibited by task or unnecessary for static audit. |

## 18. Unknowns and required follow-up evidence

- UNKNOWN — requires live run: exact runtime truth fields for one real PT-BR `/chat` request in the current local environment.
- UNKNOWN — requires live run: which strategy path the dispatcher selects for the sample PT-BR request.
- UNKNOWN — requires live run: whether Node is available and which candidate module is selected on the target host.
- UNKNOWN — requires live run: whether any configured provider env exists in the runtime environment. This audit intentionally did not print or inspect secret values.
- UNKNOWN — no caller found: `SpecialistCoordinator` direct runtime use in the inspected chat path snippets; construction is confirmed, tests exist, but a direct call in one chat turn was not proven.
- UNKNOWN — file not found: `platform/providers/remoteProviderExecutor.js`, OpenRouter runtime adapter, LM Studio adapter, Hermes adapter.
- UNKNOWN — insufficient evidence: exact concurrency behavior under simultaneous chat requests; code suggests non-atomic writes in several stores, but no stress test was run.


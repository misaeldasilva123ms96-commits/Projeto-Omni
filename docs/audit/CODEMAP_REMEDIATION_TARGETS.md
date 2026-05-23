# CODEMAP REMEDIATION TARGETS — Projeto Omni
Date: 2026-04-30
Base branch: audit/remediation-baseline-00
Base commit: a44220225017d2816e6208b23d3d49d453b907a9
Phase: 0.5
Statement: discovery only; no runtime behavior changed.

## Summary
- Found targets: shell/tool execution surfaces, filesystem read/write surfaces, git command surfaces, QueryEngine authority, execution provenance, provider router, Supabase clients/importers, runtime debug panel, learning logger, public runtime status/signals, cognitive runtime inspector, governed tools, governance controller, Python/Node/frontend/Rust test structures, package scripts, pytest/Vite/Cargo configs, OMNI/OMINI env variables.
- Missing targets: exact standalone `public_runtime_outcome` module/file not found; exact `ALLOW_SHELL*`, `PUBLIC_DEMO*`, and `DEBUG_INTERNAL*` env matches not found; standalone Jest config not found; standalone Vitest config not found because Vitest is configured through `frontend/vite.config.ts`.
- Ambiguous targets: shell/filesystem/git tools are spread across `backend/python/brain/runtime/engineering_tools.py`, `backend/python/brain/runtime/orchestrator.py`, `runtime/tooling/toolGovernance.js`, `backend/python/brain/runtime/control/governed_tools.py`, and Rust runtime tool crates; public runtime outcome appears represented by Rust `PublicRuntimeSignalsSummaryV1` plus frontend adapters rather than an exact file named `public_runtime_outcome`.
- Test structure: Python tests under `tests/**/test_*.py` with `pytest.ini`; Node/JS tests under `tests/**/*.test.mjs` and `tests/**/*.test.js`; frontend Vitest tests under `frontend/src/**/*.test.ts(x)`; Rust tests are inline/module tests under `backend/rust/src/**` and crates under `backend/rust/crates/**`.
- Env naming findings: both `OMNI_` and `OMINI_` prefixes exist. `OMINI_` is dominant for runtime configuration; `OMNI_` appears mainly bridge, provider hint, and constant/program naming.
- Supabase exposure/import findings: Node runtime has optional CJS importer at `storage/memory/supabaseClient.js`; frontend imports Supabase directly in `frontend/src/lib/supabase.ts`; Rust validates JWT issuer from `SUPABASE_URL` or `VITE_SUPABASE_URL`; Python telemetry posts through `SUPABASE_URL` plus service-role key path in `backend/python/brain/runtime/telemetry/supabase_tool_events.py`.

## Target Map
| Logical target | Real path(s) | Exists? | Evidence command/result | Risk note | Phase affected |
|---|---|---:|---|---|---|
| Shell tool | `backend/python/brain/runtime/engineering_tools.py`; `backend/python/brain/runtime/orchestrator.py`; `runtime/tooling/toolGovernance.js`; `backend/python/brain/runtime/tooling/tool_registry_extensions.py` | Yes | `rg -n "shell_command\|_run_command\|subprocess" ...` found `engineering_tools.py:275 def _run_command`, `toolGovernance.js:20 shell_command`, `orchestrator.py:436 shell_command` | High-risk execution surface; policy and public payload hardening likely required | Shell safety/input hardening |
| Filesystem read | `backend/python/brain/runtime/engineering_tools.py`; `backend/python/brain/runtime/control/governed_tools.py`; `backend/rust/crates/runtime/src/tools.rs`; `runtime/tooling/toolGovernance.js` | Yes | `rg -n "read_file\|filesystem_read" ...` found `engineering_tools.py:48`, `governed_tools.py:255`, `tools.rs:71`, `toolGovernance.js:7` | Read surface can leak internal files if path policy weak | Shell/tools hardening |
| Filesystem write | `backend/python/brain/runtime/engineering_tools.py`; `backend/python/brain/runtime/control/governed_tools.py`; `backend/rust/crates/runtime/src/tools.rs`; `runtime/tooling/toolGovernance.js` | Yes | `rg -n "write_file\|filesystem_write" ...` found `engineering_tools.py:54`, `governed_tools.py:261`, `tools.rs:152`, `toolGovernance.js:8` | Mutating surface; needs strict governance and auditability | Shell/tools hardening |
| Git tools | `backend/python/brain/runtime/engineering_tools.py`; `backend/python/brain/control/policy_engine.py`; `features/multiagent/specialists/advancedPlannerSpecialist.js`; `features/multiagent/specialists/codeReviewSpecialist.js` | Yes, ambiguous | `rg -n "git status\|git diff\|git_commit\|git policy" ...` found `engineering_tools.py:101-110`, `policy_engine.py`, specialists | Git mutation and commit behavior are distributed | Shell/git hardening |
| Query engine authority | `core/brain/queryEngineAuthority.js` | Yes | `git ls-files \| rg "queryEngineAuthority"` found `core/brain/queryEngineAuthority.js` | Central Node decision authority; large import fan-in | Runtime truth/execution |
| Execution provenance | `core/brain/executionProvenance.js`; `tests/runtime/executionProvenance.test.mjs` | Yes | `git ls-files \| rg "executionProvenance"` found both files | Provenance loss/mislabel risk | Runtime truth/provenance |
| Provider router | `platform/providers/providerRouter.js`; `tests/config/test_provider_registry.py`; docs provider routing | Yes | `git ls-files \| rg "providerRouter"` found `platform/providers/providerRouter.js` | Provider availability may be confused with configured status | Provider diagnostics |
| Supabase client | `storage/memory/supabaseClient.js`; `frontend/src/lib/supabase.ts` | Yes | `rg -n "supabaseClient\|@supabase/supabase-js"` found Node and frontend importers | Public key/url exposure and optional import behavior must remain explicit | Supabase/config |
| Supabase importers | `storage/memory/runtimeMemoryStore.js`; `frontend/src/lib/supabase.ts`; `frontend/src/hooks/useRequireAuth.ts`; `backend/python/brain/runtime/telemetry/supabase_tool_events.py`; `backend/rust/src/observability_auth.rs` | Yes | `rg -n "SUPABASE_URL\|SUPABASE_ANON_KEY\|@supabase/supabase-js"` found these paths | Multiple runtimes consume Supabase config differently | Supabase/config |
| Runtime debug panel | `frontend/src/components/status/RuntimePanel.tsx`; `frontend/src/components/status/RuntimeDebugSection.tsx`; `frontend/src/components/status/StatusPanel.tsx`; `frontend/src/styles.css` | Yes | `rg -n "Debug Mode\|RuntimeDebug\|runtime-debug"` found RuntimePanel and RuntimeDebugSection | Raw metadata exposure may need public/dev gating | Frontend/debug safety |
| Learning logger | `backend/python/brain/runtime/learning/learning_logger.py`; `tests/runtime/learning/test_learning_loop.py` | Yes | `git ls-files \| rg "learning_logger"` found logger | Bad labels can train bad feedback loop | Learning labels |
| Public runtime outcome | `backend/rust/src/main.rs` (`PublicRuntimeSignalsSummaryV1`); `frontend/src/lib/api/runtime.ts`; `frontend/src/lib/api/adapters.ts`; `frontend/src/types.ts` | Partial/ambiguous | `rg -n "public_runtime_outcome\|PublicRuntime\|runtime_outcome"` found no exact file, but public runtime status/signals types and adapters | Exact contract owner unclear | Public payload/runtime truth |
| Cognitive runtime inspector | `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`; `tests/runtime/observability/test_cognitive_runtime_inspector.py` | Yes | `git ls-files \| rg "cognitive_runtime_inspector"` found inspector and test | Misleading runtime mode/classification risk | Runtime truth |
| Governed tools | `backend/python/brain/runtime/control/governed_tools.py`; `tests/runtime/control/test_governed_tools.py` | Yes | `git ls-files \| rg "governed_tools"` found module and test | Strict mode/env policy must be verified | Governance/tools |
| Governance controller | `backend/python/brain/runtime/control/governance_controller.py`; `tests/runtime/control/test_governance_controller.py`; `backend/python/brain/runtime/orchestrator_services/governance_integration_service.py` | Yes | `git ls-files \| rg "governance_controller\|governance_integration"` found controller/service | Control plane may hide operational faults | Governance |
| Python tests | `tests/**/test_*.py`; `pytest.ini` | Yes | `Get-ChildItem tests -Recurse -File`; `pytest.ini` contains `testpaths = tests`, `python_files = test_*.py` | Broad tree; targeted subsets required | Test plan |
| Node/JS tests | `tests/**/*.test.mjs`; `tests/**/*.test.js`; root `package.json` scripts | Yes | `git ls-files tests \| rg "\.test\.(mjs\|js)"` and `package.json test:js-runtime` | JS tests include custom launcher and tsx e2e | Test plan |
| Frontend tests | `frontend/src/**/*.test.tsx`; `frontend/src/**/*.test.ts`; `frontend/vite.config.ts` | Yes | `git ls-files frontend/src \| rg "\.test\."`; `frontend/package.json test=vitest run` | Separate package and dependency graph | Frontend validation |
| Rust tests | `backend/rust/Cargo.toml`; `backend/rust/crates/runtime/Cargo.toml`; inline tests in Rust source | Yes | `git ls-files \| rg "Cargo.toml"` found Rust manifests | Cargo tests/check separate from npm scripts | Rust validation |
| Package scripts | `package.json`; `frontend/package.json`; `frontend/mobile/package.json`; `dist/package.json` | Yes | `node -e "require('./package.json').scripts"` and frontend equivalent | Root and frontend scripts differ; `dist/package.json` may be artifact | Test/build plan |
| Env vars | Multiple files; see Env Var Map | Yes, broad | `git ls-files + regex` found 94 OMNI/OMINI variables; no exact ALLOW_SHELL/PUBLIC_DEMO/DEBUG_INTERNAL matches | Prefix inconsistency and debug/public flags need canonical policy | Config hardening |

## Env Var Map
| Variable | Prefix | File(s) | Purpose inferred | Canonical/legacy/unknown | Notes |
|---|---|---|---|---|---|
| `OMINI_ALLOW_CRITICAL` | OMINI | `backend/python/brain/runtime/orchestrator.py` | Allows critical runtime actions | canonical | Runtime policy |
| `OMINI_ALLOW_HIGH_RISK` | OMINI | `backend/python/brain/runtime/orchestrator.py` | Allows high-risk runtime actions | canonical | Runtime policy |
| `OMINI_AVAILABLE_PROVIDERS` | OMINI | `platform/providers/providerRouter.js` | Provider order/availability hint | canonical | Node provider router |
| `OMINI_CONTINUATION_ALLOW_AUTO_ESCALATE` | OMINI | `backend/python/brain/runtime/continuation/continuation_policy.py`; docs archive | Continuation policy | canonical | Policy flag |
| `OMINI_CONTINUATION_ALLOW_AUTO_PAUSE` | OMINI | `backend/python/brain/runtime/continuation/continuation_policy.py`; docs archive | Continuation policy | canonical | Policy flag |
| `OMINI_CONTINUATION_ALLOW_REPLAN` | OMINI | `backend/python/brain/runtime/continuation/continuation_policy.py`; docs archive | Continuation policy | canonical | Policy flag |
| `OMINI_CONTINUATION_MAX_REPLANS_PER_PLAN` | OMINI | `backend/python/brain/runtime/continuation/continuation_policy.py`; docs archive | Continuation limit | canonical | Numeric limit |
| `OMINI_CONTINUATION_MAX_RETRIES_PER_STEP` | OMINI | `backend/python/brain/runtime/continuation/continuation_policy.py`; docs archive | Continuation retry limit | canonical | Numeric limit |
| `OMINI_CRITIC_RISK_THRESHOLD` | OMINI | `configs/runtimeConfig.js` | Critic risk threshold | canonical | Runtime config |
| `OMINI_DISABLE_EVOLUTION_LOOP` | OMINI | `backend/python/brain/evolution/__init__.py` | Disable evolution loop | canonical | Safety flag |
| `OMINI_E2E_API_URL` | OMINI | `tests/e2e/chat-contract.e2e.ts` | Optional live e2e API URL | canonical | Test-only |
| `OMINI_ENABLE_CRITIC` | OMINI | `backend/python/brain/runtime/orchestrator.py`; `configs/runtimeConfig.js`; docs archive | Enable critic | canonical | Runtime config |
| `OMINI_ENABLE_NODE_RUST_DIRECT` | OMINI | `runtime/execution/runtimeMode.js`; docs archive | Allow direct Node→Rust execution | canonical | Execution mode |
| `OMINI_ENABLE_REFLECTION` | OMINI | `configs/runtimeConfig.js` | Enable reflection | canonical | Runtime config |
| `OMINI_ENABLE_SELF_REPAIR` | OMINI | `backend/python/brain/runtime/self_repair/repair_policy.py`; docs/tests | Enable self-repair | canonical | Safety-sensitive |
| `OMINI_ENABLE_SIMULATION` | OMINI | `configs/runtimeConfig.js` | Enable simulation | canonical | Runtime config |
| `OMINI_EVOLUTION_ALLOW_PROMOTION` | OMINI | `backend/python/brain/runtime/evolution/governance_policy.py`; docs/tests | Allow evolution promotion | canonical | Safety-sensitive |
| `OMINI_EVOLUTION_ALLOW_VALIDATION` | OMINI | `backend/python/brain/runtime/evolution/governance_policy.py`; docs/tests | Allow evolution validation | canonical | Policy flag |
| `OMINI_EVOLUTION_BLOCK_CRITICAL` | OMINI | `backend/python/brain/runtime/evolution/governance_policy.py`; docs | Block critical evolution | canonical | Safety flag |
| `OMINI_EVOLUTION_ENABLED` | OMINI | `backend/python/brain/runtime/evolution/governance_policy.py`; docs/tests | Enable governed evolution | canonical | Safety-sensitive |
| `OMINI_EVOLUTION_INTERVAL_SECONDS` | OMINI | `backend/python/brain/evolution/evolution_loop.py` | Evolution loop interval | canonical | Numeric config |
| `OMINI_EVOLUTION_MAX_ACTIVE_PROPOSALS` | OMINI | `backend/python/brain/runtime/evolution/governance_policy.py`; docs | Evolution proposal limit | canonical | Numeric limit |
| `OMINI_EVOLUTION_MIN_SESSIONS` | OMINI | `backend/python/brain/evolution/evolution_loop.py` | Evolution minimum sessions | canonical | Numeric limit |
| `OMINI_EVOLUTION_REQUIRE_GOVERNANCE_FOR_MEDIUM_AND_ABOVE` | OMINI | `backend/python/brain/runtime/evolution/governance_policy.py`; docs | Governance threshold | canonical | Safety flag |
| `OMINI_EXECUTION_MODE` | OMINI | `backend/python/brain/runtime/rust_executor_bridge.py`; `configs/runtimeConfig.js`; docs | Execution mode selector | canonical | Runtime config |
| `OMINI_FORCE_SPECIALIST_FAILURE` | OMINI | `features/multiagent/specialists/*.js`; e2e tests | Forced failure injection | canonical | Test/diagnostic risk |
| `OMINI_GOVERNED_TOOLS_STRICT` | OMINI | `backend/python/brain/runtime/control/governed_tools.py`; tests | Strict governed tool mode | canonical | Governance safety |
| `OMINI_HIERARCHY_THRESHOLD` | OMINI | `configs/runtimeConfig.js` | Planning hierarchy threshold | canonical | Runtime config |
| `OMINI_JS_RUNTIME` | OMINI | `backend/python/brain/runtime/js_runtime_adapter.py`; `backend/python/brain/runtime/orchestrator.py`; `js-runner/queryEngineRunner.js`; docs | Selected JS runtime metadata | canonical | Bridge/runtime |
| `OMINI_JS_RUNTIME_BIN` | OMINI | `backend/python/brain/runtime/js_runtime_adapter.py`; `backend/python/brain/runtime/orchestrator.py`; `scripts/js-runtime-launcher.mjs`; docs | JS runtime binary override | canonical | Bridge/runtime |
| `OMINI_JS_RUNTIME_SELECTED` | OMINI | `backend/python/brain/runtime/orchestrator.py` | Selected JS runtime signal | canonical | Bridge/runtime |
| `OMINI_JS_RUNTIME_SOURCE` | OMINI | `backend/python/brain/runtime/js_runtime_adapter.py`; `js-runner/queryEngineRunner.js`; `scripts/js-runtime-launcher.mjs`; docs | JS runtime selection reason | canonical | Bridge/runtime |
| `OMINI_LEARNING_ALLOW_POLICY_HINTS` | OMINI | `backend/python/brain/runtime/learning/learning_policy.py`; docs | Learning policy hints | canonical | Learning |
| `OMINI_LEARNING_ALLOW_STRATEGY_RANKING` | OMINI | `backend/python/brain/runtime/learning/learning_policy.py`; docs | Learning strategy ranking | canonical | Learning |
| `OMINI_LEARNING_ENABLED` | OMINI | `backend/python/brain/runtime/learning/learning_policy.py`; docs | Enable learning loop | canonical | Learning |
| `OMINI_LEARNING_MAX_SIGNAL_WEIGHT` | OMINI | `backend/python/brain/runtime/learning/learning_policy.py`; docs | Learning signal weight | canonical | Learning |
| `OMINI_LEARNING_MIN_PATTERN_SAMPLES` | OMINI | `backend/python/brain/runtime/learning/learning_policy.py`; docs | Learning sample threshold | canonical | Learning |
| `OMINI_LEARNING_STALE_PATTERN_DAYS` | OMINI | `backend/python/brain/runtime/learning/learning_policy.py`; docs | Learning staleness window | canonical | Learning |
| `OMINI_LOG_LEVEL` | OMINI | `backend/rust/src/main.rs`; `js-runner/queryEngineRunner.js` | Debug logging level | canonical | Raw debug exposure risk |
| `OMINI_MAX_CORRECTION_DEPTH` | OMINI | `backend/python/brain/runtime/orchestrator.py`; `configs/runtimeConfig.js`; docs | Correction depth | canonical | Runtime config |
| `OMINI_MAX_ENGINEERING_ITERATIONS` | OMINI | `configs/runtimeConfig.js` | Engineering iteration limit | canonical | Runtime config |
| `OMINI_MAX_MILESTONES` | OMINI | `configs/runtimeConfig.js` | Milestone limit | canonical | Runtime config |
| `OMINI_MAX_PARALLEL_READ_STEPS` | OMINI | `backend/python/brain/runtime/orchestrator.py`; `configs/runtimeConfig.js`; docs | Parallel read limit | canonical | Filesystem read control |
| `OMINI_MAX_REFLECTION_DEPTH` | OMINI | `configs/runtimeConfig.js` | Reflection depth | canonical | Runtime config |
| `OMINI_MAX_RETRIES` | OMINI | `configs/runtimeConfig.js`; docs | Retry limit | canonical | Runtime config |
| `OMINI_MAX_STEPS` | OMINI | `backend/python/brain/runtime/orchestrator.py`; `configs/runtimeConfig.js`; docs/tests | Step limit | canonical | Runtime config |
| `OMINI_MEMORY_MIN_CONFIDENCE_FOR_SEMANTIC_RECALL` | OMINI | memory/simulation modules; docs/tests | Semantic recall confidence | canonical | Memory |
| `OMINI_MEMORY_MIN_EPISODES_FOR_SEMANTIC_FACT` | OMINI | memory modules; docs/tests | Semantic fact threshold | canonical | Memory |
| `OMINI_MEMORY_WORKING_EVENT_WINDOW` | OMINI | `backend/python/brain/runtime/memory/working/working_memory.py` | Working memory window | canonical | Memory |
| `OMINI_NEGOTIATION_MAX_DEPTH` | OMINI | `configs/runtimeConfig.js`; docs | Negotiation depth | canonical | Runtime config |
| `OMINI_ORCHESTRATION_ALLOW_ANALYSIS_ROUTING` | OMINI | `backend/python/brain/runtime/orchestration/orchestration_policy.py`; docs | Analysis routing | canonical | Orchestration |
| `OMINI_ORCHESTRATION_ALLOW_LEARNING_HINTS` | OMINI | `backend/python/brain/runtime/orchestration/orchestration_policy.py`; docs | Learning hints in routing | canonical | Orchestration/learning |
| `OMINI_ORCHESTRATION_ALLOW_TOOL_DELEGATION` | OMINI | `backend/python/brain/runtime/orchestration/orchestration_policy.py`; docs | Tool delegation | canonical | Orchestration/tools |
| `OMINI_ORCHESTRATION_MAX_LEARNING_WEIGHT` | OMINI | `backend/python/brain/runtime/orchestration/orchestration_policy.py`; docs | Learning weight cap | canonical | Orchestration/learning |
| `OMINI_PHASE39_APPLY` | OMINI | evolution engine; docs/tests | Phase 39 write apply | canonical | Safety-sensitive |
| `OMINI_PHASE39_DISABLE` | OMINI | evolution engine; docs/tests | Disable Phase 39 | canonical | Safety flag |
| `OMINI_PHASE40_APPLY` | OMINI | improvement/inspector; docs/tests | Phase 40 apply | canonical | Safety-sensitive |
| `OMINI_PHASE40_APPROVE` | OMINI | approval gate; docs/tests | Human approval | canonical | Safety flag |
| `OMINI_PHASE40_AUTO_APPROVE` | OMINI | approval gate; docs/tests | Auto approval | canonical | Safety-sensitive |
| `OMINI_PHASE40_AUTO_APPROVE_MAX_RISK` | OMINI | approval gate; docs | Auto approval risk cap | canonical | Safety-sensitive |
| `OMINI_PHASE40_DISABLE` | OMINI | improvement/inspector; docs/tests | Disable Phase 40 | canonical | Safety flag |
| `OMINI_PHASE40_ENABLE` | OMINI | improvement/inspector/orchestrator; docs/tests | Enable Phase 40 | canonical | Safety-sensitive |
| `OMINI_PHASE40_FORCE_APPROVE` | OMINI | approval gate; docs | Force approval | canonical | High risk |
| `OMINI_PHASE41_EVOLUTION_FEED` | OMINI | evolution loop; observability reader | Evolution feed | canonical | Observability/evolution |
| `OMINI_PHASE41_POLICY_ACTIVE` | OMINI | observability reader; policy router; tests | Phase 41 policy | canonical | Policy |
| `OMINI_PHASE41_POLICY_LOG` | OMINI | `backend/python/brain/runtime/orchestrator.py` | Policy logging | canonical | Log exposure risk |
| `OMINI_PUBLIC_DEBUG` | OMINI | `backend/python/main.py` | Public debug details | canonical | Public payload exposure risk |
| `OMINI_QUERY_ENGINE_ORDER` | OMINI | `js-runner/queryEngineRunner.js`; tests | QueryEngine candidate order | canonical | Runtime selection |
| `OMINI_RUNTIME_MODE` | OMINI | `backend/python/brain/runtime/orchestrator.py`; `backend/rust/src/main.rs`; tests | Runtime mode override | canonical | Misleading runtime mode risk |
| `OMINI_RUN_CONTROL_MAX_WAIT_SECONDS` | OMINI | governance integration/control tests | Governance wait timeout | canonical | Governance |
| `OMINI_RUN_CONTROL_POLL_SECONDS` | OMINI | governance integration/control tests | Governance poll interval | canonical | Governance |
| `OMINI_SELF_REPAIR_ALLOWED_ROOT` | OMINI | self-repair policy; docs | Allowed repair root | canonical | File safety |
| `OMINI_SELF_REPAIR_ALLOW_PROMOTION` | OMINI | self-repair policy; docs | Self-repair promotion | canonical | Safety-sensitive |
| `OMINI_SELF_REPAIR_MAX_ATTEMPTS_PER_ACTION` | OMINI | self-repair policy; docs | Attempt limit | canonical | Safety |
| `OMINI_SELF_REPAIR_MAX_FILES` | OMINI | self-repair policy; docs | File limit | canonical | File safety |
| `OMINI_SELF_REPAIR_MAX_RECURRENCE` | OMINI | self-repair policy; docs | Recurrence limit | canonical | Safety |
| `OMINI_SEMANTIC_MODE` | OMINI | `configs/runtimeConfig.js` | Semantic retrieval mode | canonical | Memory |
| `OMINI_SKIP_CONVERSATIONAL_MATCHERS` | OMINI | `core/brain/queryEngineAuthority.js` | Disable conversational matchers | canonical | Runtime behavior |
| `OMINI_STALE_CHECKPOINT_MINUTES` | OMINI | orchestrator/config | Stale checkpoint window | canonical | Runtime config |
| `OMINI_STEP_TIMEOUT_MS` | OMINI | `configs/runtimeConfig.js`; docs | Step timeout | canonical | Runtime config |
| `OMINI_SUPABASE_TOOL_EVENTS_DISABLE` | OMINI | `backend/python/brain/runtime/telemetry/supabase_tool_events.py`; `omni/model/OMNI_ANALYTICS_SETUP.txt` | Disable Supabase tool telemetry | canonical | Supabase/logging |
| `OMINI_SUPERVISION_MAX_BRANCHES` | OMINI | `configs/runtimeConfig.js` | Supervision branch limit | canonical | Runtime config |
| `OMINI_SUPERVISION_MAX_TREE_NODES` | OMINI | `configs/runtimeConfig.js` | Supervision tree limit | canonical | Runtime config |
| `OMNI_AGENT_POLICIES` | OMNI | `docs/architecture/system-overview.md` | Documentation link token | legacy/unknown | Not runtime env |
| `OMNI_AVAILABLE_PROVIDERS` | OMNI | `backend/python/brain/runtime/js_runtime_adapter.py`; docs/tests | Provider list propagated to Node | legacy/bridge | Bridge naming differs from OMINI |
| `OMNI_BRIDGE_` | OMNI | backend docs | Bridge prefix docs | legacy/bridge | Prefix placeholder in docs |
| `OMNI_BRIDGE_CLIENT_SESSION_ID` | OMNI | `backend/python/brain/runtime/bridge_stdin.py`; `orchestrator.py`; docs | Client session bridge | legacy/bridge | Rust→Python correlation |
| `OMNI_BRIDGE_REQUEST_SOURCE` | OMNI | `backend/python/brain/runtime/bridge_stdin.py`; docs | Request source bridge | legacy/bridge | Rust→Python correlation |
| `OMNI_BRIDGE_RUNTIME_SESSION_VERSION` | OMNI | `backend/python/brain/runtime/bridge_stdin.py`; docs | Runtime session version bridge | legacy/bridge | Rust→Python correlation |
| `OMNI_COGNITIVE_CONTROL_LAYER` | OMNI | docs | Documentation link token | legacy/unknown | Not runtime env |
| `OMNI_OIL_PROGRAM_RANGE` | OMNI | `backend/python/brain/runtime/language/__init__.py`; tests | OIL program constant | legacy/constant | Program marker |
| `OMNI_POLICY_HINT_JSON` | OMNI | `backend/python/brain/runtime/orchestrator.py`; `core/brain/executionProvenance.js`; docs/tests | Policy hint bridge to Node | legacy/bridge | Provider/provenance |
| `OMNI_RUNTIME_CONVERGENCE_PHASE` | OMNI | `backend/python/brain/runtime/control/program_closure.py`; tests | Program constant | legacy/constant | Control closure |
| `OMNI_RUNTIME_CONVERGENCE_PROGRAM` | OMNI | `backend/python/brain/runtime/control/program_closure.py`; tests | Program constant | legacy/constant | Control closure |
| `ALLOW_SHELL*` | OTHER | No matches | Shell allow env not found | missing | `rg -n "ALLOW_SHELL"` returned no matches |
| `PUBLIC_DEMO*` | OTHER | No matches | Public demo env not found | missing | `rg -n "PUBLIC_DEMO"` returned no matches |
| `DEBUG_INTERNAL*` | OTHER | No matches | Internal debug env not found | missing | `rg -n "DEBUG_INTERNAL"` returned no matches |

## Supabase Map
| File | Import/export pattern | Exposes key/url? | Public risk | Notes |
|---|---|---:|---|---|
| `storage/memory/supabaseClient.js` | CJS `require('@supabase/supabase-js')`; exports `supabase`, `supabaseKey`, `supabaseUrl`, `isSupabaseConfigured`, diagnostics | Yes, module exports key/url values internally | Medium if surfaced through debug/log payloads | Node runtime memory client; optional package behavior exists in current baseline |
| `storage/memory/runtimeMemoryStore.js` | Imports `isSupabaseConfigured`, `supabase`, `supabaseUrl` from local client | Indirectly uses URL in semantic metadata | Medium | Runtime memory falls back local when not configured |
| `frontend/src/lib/supabase.ts` | ESM `import { createClient } from '@supabase/supabase-js'`; exports browser client | Uses public anon key/url | Medium/public | Browser-safe only if anon key and policies are safe |
| `frontend/src/lib/env.ts` | Resolves `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY` | Yes, frontend env values | Medium/public | Explicit browser config surface |
| `frontend/src/hooks/useRequireAuth.ts` | Type import from Supabase package | No direct key/url | Low | Auth hook type dependency |
| `backend/rust/src/observability_auth.rs` | Reads `SUPABASE_URL` or `VITE_SUPABASE_URL` for issuer validation | URL only | Low/medium | JWT issuer validation |
| `backend/python/config/secrets_manager.py` | Maps `SUPABASE_URL` and `SUPABASE_ANON_KEY` | Values handled as secrets/config | Medium | Centralized provider secret manager |
| `backend/python/brain/runtime/telemetry/supabase_tool_events.py` | Reads `SUPABASE_URL`, service role key path inferred by comment | Could use service role key | High if leaked | Tool telemetry write path must remain server-only |
| `.env.example`, `frontend/.env.example`, `frontend/Dockerfile` | Example/ARG env declarations | Placeholder/example | Low if placeholders stay fake | Public examples must not contain real values |

## Test Map
| Test command/script | Defined where | Exists? | Likely scope | Notes |
|---|---|---:|---|---|
| `npm test` | root `package.json` | Yes | JS runtime suite then Python unittest discovery | Root meta-test |
| `npm run test:js-runtime` | root `package.json` | Yes | Fusion, package QueryEngine, runtime mode, smoke, runner, adapter-first, Supabase optional, specialists, e2e chat contract | Uses `scripts/js-runtime-launcher.mjs` |
| `npm run test:node` | root `package.json` | Yes | Alias to `test:js-runtime` | Node runtime |
| `npm run test:python` | root `package.json` | Yes | `python -m unittest discover -s tests -p test_*.py` | Python unittest discovery |
| `npm run test:python:pytest` | root `package.json` | Yes | Contracts/integration/runtime subsets with coverage | Pytest configured by `pytest.ini` |
| `npm run test:python:pytest:audit` | root `package.json` | Yes | Performance + contract audit | Audit subset |
| `npm run test:e2e:chat-contract` | root `package.json` | Yes | TSX chat wire contract; optional live URL via `OMINI_E2E_API_URL` | E2E/contract |
| `npm run test:queryengine` | root `package.json` | Yes | QueryEngine smoke test | Node |
| `npm run check:queryengine` | root `package.json` | Yes | QueryEngine static/check script | Node |
| `npm --prefix frontend test` | `frontend/package.json` | Yes | Vitest plus runtime console verification script | Frontend |
| `npm --prefix frontend run typecheck` | `frontend/package.json` | Yes | TypeScript typecheck | Frontend |
| `npm --prefix frontend run build` | `frontend/package.json` | Yes | Vite build | Frontend |
| `cargo test` / `cargo check` | `backend/rust/Cargo.toml` | Manifest exists | Rust API and runtime crate | Not wired into root npm scripts |

## Missing / Ambiguous
- Missing exact file/module named `public_runtime_outcome`; related public runtime contracts exist in `backend/rust/src/main.rs`, `frontend/src/lib/api/runtime.ts`, `frontend/src/lib/api/adapters.ts`, and `frontend/src/types.ts`.
- Missing env matches for `ALLOW_SHELL*`, `PUBLIC_DEMO*`, and `DEBUG_INTERNAL*`.
- Missing standalone `jest.config.*`; no Jest config found.
- Missing standalone `vitest.config.*`; Vitest config is embedded in `frontend/vite.config.ts`.
- Ambiguous shell/filesystem/git implementation ownership because Python orchestration, governed tools, JS tool governance, and Rust runtime tools all reference tool names.
- Ambiguous provider availability semantics because `OMINI_AVAILABLE_PROVIDERS` and `OMNI_AVAILABLE_PROVIDERS` both exist in different bridge contexts.
- Supabase importer surface is multi-runtime and exposes different risk levels: browser anon client, Node memory client, Rust issuer validation, Python telemetry writes.

## Gate 0.5
PASSED

Evidence:
- All remediation target categories were searched with `git ls-files`, `rg`, `Get-ChildItem`, and package/config inspection.
- Real paths are documented in the target map.
- Missing files and missing env families are explicit.
- Test structure is mapped across Python, Node/JS, frontend, and Rust.
- Env var naming is mapped for all detected `OMNI_*` and `OMINI_*` variables plus missing `ALLOW_SHELL*`, `PUBLIC_DEMO*`, and `DEBUG_INTERNAL*` families.
- Supabase importers are mapped.
- No behavior changed.
- No merge into main.

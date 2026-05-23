# Omni - Cognitive Runtime System

> Not a chatbot.
> Omni is an experimental runtime that decides, executes, observes, evaluates, and learns.

Omni is a multi-runtime cognitive system designed to make AI execution visible, testable, and improvable. Instead of treating each interaction as a text-only response, Omni models a full runtime loop: intent interpretation, strategy selection, action execution, observability, decision evaluation, and controlled learning.

This repository is open for public debugging and contribution. The project is functional in several core paths and has current runtime/security hardening, but it remains a controlled-demo/research system, not a production system.

---

## Why Omni Exists

Most AI applications expose only the final answer. That makes it difficult to know:

- why a strategy was selected
- whether a tool actually ran
- which provider was used
- whether fallback happened
- whether a failure was hidden behind generic text
- whether the system learned anything useful from the turn

Omni is built around runtime truth. Every meaningful turn should be inspectable, attributable, and testable.

---

## Core Runtime Loop

```txt
Input -> Decision -> Execution -> Observation -> Evaluation -> Learning
```

Omni aims to make this loop:

- explicit
- traceable
- failure-safe
- testable
- useful for future training and controlled evolution

---

## What Omni Can Do Today

Current working areas include:

- real execution paths through the Node runtime and local tools
- truthful runtime classification
- structured bridge failure handling
- multi-provider routing and provider diagnostics
- session-only bring-your-own-key (BYOK) boundary with fail-closed execution policy
- tool execution diagnostics
- frontend runtime debug visibility
- decision quality validation
- controlled learning records and improvement signals
- public-safe runner smoke diagnostics for deployment debugging

Current provider support:

- Remote adapters: Groq, OpenRouter, OpenAI, Anthropic, Gemini
- Local adapters: Ollama, LM Studio
- Embedded fallback: `local-heuristic`
- Registered but non-executable: DeepSeek

Normal fallback order:

```txt
Groq -> OpenRouter -> OpenAI -> Anthropic -> Gemini -> Ollama -> LM Studio -> local-heuristic
```

Provider execution is configuration-gated. Cloud providers require their API key env var. Local providers are not attempted just because a localhost default exists; Ollama requires `OLLAMA_URL`, and LM Studio requires `LMSTUDIO_URL`.

The default JavaScript runtime is Node. Bun is opt-in only through `OMINI_JS_RUNTIME_BIN=bun`. The legacy-compatible alias `OMNI_JS_RUNTIME_BIN` may be used when `OMINI_JS_RUNTIME_BIN` is unset.

Current active work:

- improving decision quality for ambiguous prompts
- increasing tool/action reliability across environments
- expanding evaluation datasets
- improving adaptive routing without uncontrolled self-modification
- hardening frontend and bridge behavior for public contributors

---

## Architecture

Omni is distributed across four main runtimes:

| Layer | Responsibility | Main Areas |
| --- | --- | --- |
| Rust API Layer | HTTP/API boundary, process bridge, response contract | `backend/rust/` |
| Python Brain Runtime | orchestration, governance, runtime classification, learning | `backend/python/brain/runtime/` |
| Node/Bun Execution Layer | provider routing, tool/action execution, runtime authority | `core/`, `js-runner/`, `platform/` |
| React/Vite Interface | chat console, runtime debug surface, developer visibility | `frontend/` |

Core system layers:

- Decision Layer - strategy and execution selection
- Execution Layer - tools, actions, Node runtime, provider calls
- Observability Layer - runtime truth, provenance, inspection
- Governance Layer - control, policy, operational timeline
- Provider Layer - routing, diagnostics, fallback visibility
- Learning Layer - local records, decision evaluation, improvement signals

Current default execution path:

```txt
Rust/Axum HTTP API
  -> Python subprocess BrainOrchestrator
  -> Node subprocess QueryEngine runner
  -> Python public payload sanitization
  -> Rust HTTP response
```

Python and Node service modes exist behind configuration, but they are opt-in. The default contributor and controlled-demo path remains subprocess based.

Architecture references:

- [docs/overview.md](docs/overview.md)
- [docs/architecture/layers.md](docs/architecture/layers.md)
- [docs/architecture/runtime-flow.md](docs/architecture/runtime-flow.md)
- [docs/architecture/runtime-modes.md](docs/architecture/runtime-modes.md)
- [docs/architecture/bridge-response-contract.md](docs/architecture/bridge-response-contract.md)
- [docs/architecture/bridge-pipeline.md](docs/architecture/bridge-pipeline.md)
- [docs/architecture/provider-routing.md](docs/architecture/provider-routing.md)
- [docs/runtime/current-state-runtime-audit.md](docs/runtime/current-state-runtime-audit.md)
- [docs/runtime/providers.md](docs/runtime/providers.md)
- [docs/runtime/byok.md](docs/runtime/byok.md)
- [docs/runtime/diagnostics.md](docs/runtime/diagnostics.md)
- [docs/architecture/tool-runtime.md](docs/architecture/tool-runtime.md)
- [docs/architecture/cognitive-decision-model.md](docs/architecture/cognitive-decision-model.md)
- [docs/architecture/learning-loop.md](docs/architecture/learning-loop.md)

---

## Runtime Truth

Omni exposes structured metadata so contributors can verify what actually happened:

- `runtime_mode`
- `runtime_reason`
- `execution_path_used`
- `fallback_triggered`
- `compatibility_execution_active`
- `provider_actual`
- `provider_failed`
- `failure_class`
- `execution_provenance`
- `tool_execution`
- `provider_diagnostics`
- `provider_diagnostics_snapshot`
- `cognitive_runtime_inspection`
- `learning signals`

The goal is simple: no hidden degradation, no fake success, and no pretending that a fallback path was full cognitive execution.

Important runtime modes:

| Mode | Meaning |
| --- | --- |
| `FULL_COGNITIVE_RUNTIME` | Explicit evidence shows provider/tool/action execution completed through the full cognitive path. |
| `PARTIAL_COGNITIVE` / `PARTIAL_COGNITIVE_RUNTIME` | A real non-fallback result exists, but evidence is not strong enough for full runtime. |
| `MATCHER_SHORTCUT` | A local matcher answered without provider or tool execution. |
| `RULE_BASED_INTENT` | Intent came from rules/regex classification rather than an LLM classifier. |
| `COMPATIBILITY_EXECUTION` | The compatibility path completed; supported but not the long-term happy path. |
| `SAFE_DEGRADED_FALLBACK` / `SAFE_FALLBACK` | The system intentionally returned a controlled degraded/fallback response. |

Transport success is not cognitive success. HTTP 200, valid JSON, `status=success`, or `NODE_EXECUTION_SUCCESS` only prove that a boundary returned a usable payload. Contributors must inspect runtime truth, provider diagnostics, tool execution, and fallback flags before claiming full cognitive execution.

Public-safe runner diagnostic:

```txt
GET /api/v1/runtime/runner-smoke
```

This endpoint executes the same Node runner path used by chat with a fixed safe prompt. It returns only bounded public fields such as selected runtime, path-existence booleans, JSON validity, degraded status, and a public failure class. It must never expose raw stdout/stderr, env values, stack traces, headers, provider payloads, API keys, request bodies, or absolute local paths.

---

## Learning Loop

Omni records runtime outcomes as local learning records:

```json
{
  "input": "...",
  "selected_strategy": "...",
  "selected_tool": "...",
  "execution_path": "...",
  "runtime_mode": "...",
  "success": true,
  "failure_class": null,
  "decision_correct": true,
  "timestamp": "..."
}
```

The learning layer can generate advisory improvement signals, such as:

- prefer a file tool for file-analysis prompts
- reduce fallback usage when execution was possible
- improve routing for repeated misdecision patterns

Important safety rule: Omni does not automatically rewrite or mutate itself. Learning signals are observable recommendations, not self-applied code changes.

Runtime success is not automatically a positive training candidate. Positive export requires explicit `learning_safety.positive_training_candidate=true`, redaction, safe runtime mode, no fallback/matcher/provider failure/governance block/tool failure, and user-visible success. See [docs/training/TRAINING_READINESS.md](docs/training/TRAINING_READINESS.md).

---

## Project Status

Omni is experimental and under active development.

Stable enough for:

- runtime architecture review
- frontend/runtime debugging
- provider and tool diagnostics
- contribution to tests, docs, observability, and execution reliability
- controlled demo validation in a locked-down environment

Not yet stable enough for:

- production decision automation
- unattended high-impact actions
- claims of general autonomous reliability
- uncontrolled self-improvement
- public production deployment
- training data collection without the documented safety gates

Public debug references:

- [docs/public-debug/PROJECT_STATUS.md](docs/public-debug/PROJECT_STATUS.md)
- [docs/public-debug/KNOWN_ISSUES.md](docs/public-debug/KNOWN_ISSUES.md)
- [docs/public-debug/REPRODUCTION.md](docs/public-debug/REPRODUCTION.md)
- [docs/public-debug/CONTRIBUTOR_TASKS.md](docs/public-debug/CONTRIBUTOR_TASKS.md)
- [docs/public-debug/LEARNING_DEBUGGING.md](docs/public-debug/LEARNING_DEBUGGING.md)

---

## Repository Map

```txt
backend/rust/                 Rust API and bridge boundary
backend/python/               Python cognitive runtime
backend/python/brain/runtime/ Orchestration, control, observability, learning
core/                         Node runtime authority and provider logic
js-runner/                    Node execution runner
platform/                     Provider/tool platform code
frontend/                     React/Vite cognitive runtime console
docs/                         Architecture, audits, public debug docs
tests/                        Runtime, contract, integration, cognitive tests
omni-training/                Training/evaluation experiments
```

---

## Getting Started

Clone and configure:

```bash
git clone <repo>
cd project
cp .env.example .env
```

Install root dependencies:

```bash
npm install
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Install Python dependencies:

```bash
pip install -r backend/python/requirements.txt
```

Optional training dependencies:

```bash
pip install -r omni-training/requirements.txt
```

---

## Running Locally

Run the Python runtime directly:

```bash
python backend/python/main.py
```

Run the Rust API:

```bash
cargo run --manifest-path backend/rust/Cargo.toml
```

Run the frontend:

```bash
cd frontend
npm run dev
```

Default local frontend:

```txt
http://127.0.0.1:5173
```

Some preview/deploy flows may serve the built frontend on:

```txt
http://127.0.0.1:4173
```

---

## Validation

Current local validation matrix:

```bash
cargo test
npm run test:js-runtime
npm run test:python:pytest
npm run test:security
npm run validate:public-demo
npm run validate:audit-pack
```

Frontend validation:

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

Python runtime validation examples:

```bash
python -m pytest -q tests/runtime/observability/test_runtime_truth_contract.py
python -m pytest -q tests/runtime/test_tool_governance_enforcement.py
python -m pytest -q tests/training/test_training_readiness_phase13.py
```

Live HTTP E2E depends on `OMINI_E2E_API_URL` and may skip when no local API URL is configured. `npm run test:integration` and `npm run intake:validate` are not current root scripts unless added later. Use only the validations relevant to the files you changed. If a validation cannot be run, document why in the PR.

See [docs/operations/testing.md](docs/operations/testing.md).

---

## Frontend Runtime Console

The current UI is a cognitive runtime console, not a simple chat window. It exposes:

- chat execution state
- runtime mode
- execution path
- provider diagnostics
- tool diagnostics
- failure class
- debug mode with sanitized public metadata
- responsive panels for chat, tools, and runtime state

Frontend code:

- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/components/chat/ChatPanel.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/status/RuntimePanel.tsx`
- `frontend/src/state/runtimeConsoleStore.ts`

---

## Contributing

Contributions are welcome, especially in:

- runtime execution reliability
- strategy and decision quality
- tool/action integrations
- provider diagnostics
- observability and provenance
- frontend debugging UX
- test coverage
- public documentation
- cognitive evaluation datasets

Start here:

1. [CONTRIBUTING.md](CONTRIBUTING.md)
2. [docs/public-debug/PROJECT_STATUS.md](docs/public-debug/PROJECT_STATUS.md)
3. [docs/public-debug/REPRODUCTION.md](docs/public-debug/REPRODUCTION.md)
4. [docs/public-debug/CONTRIBUTOR_TASKS.md](docs/public-debug/CONTRIBUTOR_TASKS.md)

Contribution rules:

- do not commit secrets
- do not hide broken runtime behavior
- do not remove diagnostics to make tests pass
- do not claim full execution when fallback was used
- add or update tests for behavior changes
- document any remaining uncertainty

---

## Roadmap

The repository has multiple roadmap tracks: public debug/runtime truth, security remediation/hardening, and longer-term product maturity. Do not treat the project as simply "Phase 9 of 10"; use the current roadmap index and audit docs.

Next focus areas:

- keeping documentation synchronized with audited runtime behavior
- increasing integration confidence across Rust, Python, Node, and frontend surfaces
- hardening opt-in service modes
- expanding safe evaluation datasets
- improving routing without weakening runtime truth or governance gates

See [ROADMAP.md](ROADMAP.md).

---

## Security and Public Debug Policy

This repository should keep code, tests, docs, and example configuration public.

Do not commit:

- API keys
- tokens
- passwords
- private `.env` files
- private memory stores
- real user conversations
- local databases
- private datasets
- logs containing secrets or personal data

See:

- [.env.example](.env.example)
- [docs/public-debug/PUBLIC_SAFETY_AUDIT.md](docs/public-debug/PUBLIC_SAFETY_AUDIT.md)
- [docs/audit/KNOWN_LIMITATIONS.md](docs/audit/KNOWN_LIMITATIONS.md)
- [docs/release/PUBLIC_DEMO_READINESS.md](docs/release/PUBLIC_DEMO_READINESS.md)

---

## Philosophy

Omni is built on one principle:

> A system is only as good as its ability to explain and improve its own decisions.

The long-term goal is not just better answers. It is a transparent, executable, observable, and evolvable cognitive runtime.

---

## License

See [LICENSE](LICENSE).

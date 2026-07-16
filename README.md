# Omni — Governed Cognitive Runtime

> Not a chatbot. Omni is an experimental governed runtime for making AI execution visible, inspectable, testable, and safer to evolve.

Omni is a multi-runtime AI system designed around **runtime truth**. Instead of exposing only a final answer, Omni models the full execution loop: intent interpretation, strategy selection, provider/tool routing, action execution, observability, evaluation, and controlled learning signals.

This repository is public for debugging, research, and contribution. Omni has functional runtime, provider, frontend, observability, and governance foundations, but it is still a **controlled-demo/research system**, not a production automation platform.

---

## Current Status

| Area | Current state |
| --- | --- |
| Runtime | Rust API → Python Brain runtime → Node QueryEngine runner, with public-safe response sanitization. |
| Frontend | Omni Cockpit / runtime console with chat, Runtime Truth, Runtime Inspector, provider visibility, observability, governance, memory, agents, projects, token usage, and lab surfaces. |
| Providers | Configuration-gated remote adapters plus local provider support and local heuristic fallback. |
| Routing | Provider auto-routing foundation with safe runtime metadata and inspector visibility. |
| Token handling | Governed token compression foundation with fail-closed safety boundaries and metadata-only runtime truth. |
| Cost / quota | Provider quota and cost dashboard foundation based on safe diagnostics and optional safe metadata, not real billing integrations. |
| Agent gateway | Internal governed agent gateway foundation with allowlisted capability metadata and sensitive capabilities denied by default. |
| Learning | Local learning records and advisory improvement signals. No automatic self-rewrite or uncontrolled self-improvement. |
| Public posture | Open research/debug repository with explicit safety, documentation, and manual-merge rules. |

Recent verified cycle:

- #490 — OmniRoute architectural reference study and ADRs.
- #491 — Provider Auto Routing foundation.
- #492 — Provider Auto Routing visibility in Runtime Inspector.
- #493 — Governed Token Compression foundation.
- #494 — Provider Quota & Cost Dashboard foundation.
- #495 — Governed Agent Gateway foundation.
- #496 — OmniRoute adaptation-cycle summary and compliance closure.

OmniRoute is documented only as an architectural reference. Omni does **not** copy OmniRoute code and does **not** adopt MITM, TLS stealth, proxy/bypass, scraping, unofficial endpoints, sensitive credential import, direct OmniRoute integration, real MCP/A2A, real billing, or external private endpoints.

---

## Why Omni Exists

Most AI applications make it hard to verify what actually happened. A response can look successful even when a provider failed, a fallback answered, a matcher shortcut ran, or a tool was never executed.

Omni is built so each meaningful turn can expose:

- selected runtime path;
- provider attempted and provider used;
- fallback or degraded execution;
- tool/governance decisions;
- sanitized diagnostics;
- learning and evaluation signals;
- evidence that separates transport success from cognitive success.

Core loop:

```txt
Input -> Decision -> Execution -> Observation -> Evaluation -> Learning Signal
```

---

## Architecture

Omni is organized across four major runtime surfaces:

| Layer | Responsibility | Main paths |
| --- | --- | --- |
| Rust API Layer | HTTP boundary, bridge process control, public response contract | `backend/rust/` |
| Python Brain Runtime | orchestration, governance, runtime classification, learning, sanitization | `backend/python/brain/runtime/` |
| Node Execution Layer | provider routing, tool/action execution, QueryEngine runner | `core/`, `js-runner/`, `platform/` |
| React/Vite Frontend | Omni Cockpit, chat, runtime inspector, observability and debug UI | `frontend/` |

Default controlled-demo execution path:

```txt
Rust/Axum HTTP API
  -> Python subprocess BrainOrchestrator
  -> Node subprocess QueryEngine runner
  -> Python public payload sanitization
  -> Rust HTTP response
```

Python and Node service modes exist behind configuration, but the default contributor path remains subprocess-based unless explicitly enabled.

---

## Runtime Truth

Runtime Truth is the project’s central contract. Transport-level success is not enough. HTTP `200`, valid JSON, `status=success`, or `NODE_EXECUTION_SUCCESS` do not by themselves prove full cognitive execution.

Important runtime evidence includes:

- `runtime_mode` and `runtime_reason`;
- `execution_path_used`;
- `fallback_triggered`;
- `provider_actual` and `provider_failed`;
- `failure_class`;
- `execution_provenance`;
- `tool_execution`;
- `provider_diagnostics`;
- `provider_auto_routing`;
- `token_compression`;
- `provider_usage_summary`;
- `governed_agent_gateway`;
- `cognitive_runtime_inspection`;
- learning and safety signals.

Representative modes:

| Mode | Meaning |
| --- | --- |
| `FULL_COGNITIVE_RUNTIME` | Evidence shows provider/tool/action execution completed through the full path. |
| `PARTIAL_COGNITIVE` / `PARTIAL_COGNITIVE_RUNTIME` | A real non-fallback result exists, but evidence is not strong enough for full runtime. |
| `MATCHER_SHORTCUT` | A local matcher answered without provider/tool execution. |
| `RULE_BASED_INTENT` | Intent came from rules/regex classification rather than an LLM classifier. |
| `COMPATIBILITY_EXECUTION` | Compatibility path completed; supported but not the long-term happy path. |
| `SAFE_DEGRADED_FALLBACK` / `SAFE_FALLBACK` | The system intentionally returned a controlled degraded/fallback response. |

---

## Provider And Execution Policy

Current provider support:

- Remote adapters: Groq, OpenRouter, OpenAI, Anthropic, Gemini.
- Local adapters: Ollama, LM Studio.
- Embedded fallback: `local-heuristic`.
- Registered but non-executable: DeepSeek.

Normal fallback order:

```txt
Groq -> OpenRouter -> OpenAI -> Anthropic -> Gemini -> Ollama -> LM Studio -> local-heuristic
```

Provider execution is configuration-gated. Cloud providers require their API key environment variable. Local providers are not attempted only because a localhost default exists; Ollama requires `OLLAMA_URL`, and LM Studio requires `LMSTUDIO_URL`.

The default JavaScript runtime is Node. Bun is opt-in through the canonical `OMNI_JS_RUNTIME_BIN=bun` setting.

---

## Repository Map

```txt
backend/rust/                 Rust API and bridge boundary
backend/python/               Python cognitive runtime and sanitization
backend/python/brain/runtime/ Orchestration, control, observability, learning
core/                         Node runtime authority and provider logic
js-runner/                    QueryEngine and Node execution runner
platform/                     Provider/tool platform code
frontend/                     React/Vite Omni Cockpit
frontend/src/                 App shell, chat, runtime, observability, providers
docs/                         Canonical documentation home
tests/                        Runtime, contract, security, integration, cognitive tests
omni-training/                Training/evaluation experiments
```

---

## Getting Started

```bash
git clone https://github.com/misaeldasilva123ms96-commits/Projeto-Omni.git
cd Projeto-Omni
cp .env.example .env
npm install
```

Install optional subproject dependencies as needed:

```bash
pip install -r backend/python/requirements.txt
pip install -r omni-training/requirements.txt
cd frontend && npm install
```

Run the main surfaces:

```bash
# Python runtime
python backend/python/main.py

# Rust API
cargo run --manifest-path backend/rust/Cargo.toml

# Frontend
cd frontend
npm run dev
```

Default local frontend:

```txt
http://127.0.0.1:5173
```

---

## Validation

Root validation examples:

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

Use the validation relevant to the files changed. If a validation cannot be run locally, document the reason in the PR.

---

## Documentation

Start with:

- [docs/README.md](docs/README.md) — documentation index.
- [docs/status/current-state.md](docs/status/current-state.md) — current verified repository state.
- [ROADMAP.md](ROADMAP.md) — roadmap and active priorities.
- [GOVERNANCE.md](GOVERNANCE.md) — non-negotiable project governance.
- [docs/overview.md](docs/overview.md) — concise project overview.
- [docs/architecture/](docs/architecture/) — runtime, layers, bridge, provider, tool, and learning architecture.
- [docs/runtime/](docs/runtime/) — providers, BYOK, diagnostics, and runtime audits.
- [docs/public-debug/](docs/public-debug/) — public debug status, reproduction, known issues, contributor tasks.
- [docs/operations/testing.md](docs/operations/testing.md) — testing matrix.
- [docs/training/TRAINING_READINESS.md](docs/training/TRAINING_READINESS.md) — training safety gates.

---

## Contributing

Contributions are welcome in:

- runtime execution reliability;
- provider routing and diagnostics;
- runtime truth and observability;
- frontend Cockpit UX and inspector clarity;
- test coverage;
- public documentation;
- safety and governance hardening.

Rules:

- never commit secrets, tokens, local `.env` files, private memory stores, or real user conversations;
- never hide degraded behavior behind generic success messaging;
- never claim full execution when fallback, matcher, or compatibility paths were used;
- keep PRs small, scoped, and evidence-based;
- do not merge into `main` automatically. Main merges remain manual.

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Project Boundaries

Omni is not currently production-ready for high-impact unattended automation. It should not be presented as a finished autonomous agent platform.

Omni does not authorize:

- automatic main merges;
- uncontrolled self-modification;
- production decision automation;
- secret exposure;
- bypassing third-party controls;
- MITM, TLS stealth, proxy/bypass, scraping, or unofficial endpoint use;
- training export without documented safety gates.

---

## License

See [LICENSE](LICENSE).

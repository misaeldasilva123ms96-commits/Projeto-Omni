# Omni - Cognitive Runtime System

> Not a chatbot.
> Omni is an experimental runtime that decides, executes, observes, evaluates, and learns.

Omni is a multi-runtime cognitive system designed to make AI execution visible, testable, and improvable. Instead of treating each interaction as a text-only response, Omni models a full runtime loop: intent interpretation, strategy selection, action execution, observability, decision evaluation, and controlled learning.

This repository is open for public debugging and contribution. The project is functional in several core paths, but still experimental and actively evolving.

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
- provider diagnostics
- tool execution diagnostics
- frontend runtime debug visibility
- decision quality validation
- controlled learning records and improvement signals

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

Architecture references:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/overview.md](docs/overview.md)
- [docs/architecture/layers.md](docs/architecture/layers.md)
- [docs/architecture/runtime-flow.md](docs/architecture/runtime-flow.md)
- [docs/architecture/runtime-modes.md](docs/architecture/runtime-modes.md)
- [docs/architecture/bridge-pipeline.md](docs/architecture/bridge-pipeline.md)
- [docs/architecture/provider-routing.md](docs/architecture/provider-routing.md)
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
- `cognitive_runtime_inspection`
- `learning signals`

The goal is simple: no hidden degradation, no fake success, and no pretending that a fallback path was full cognitive execution.

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

---

## Project Status

Omni is experimental and under active development.

Stable enough for:

- runtime architecture review
- frontend/runtime debugging
- provider and tool diagnostics
- contribution to tests, docs, observability, and execution reliability

Not yet stable enough for:

- production decision automation
- unattended high-impact actions
- claims of general autonomous reliability
- uncontrolled self-improvement

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

Common validation commands:

```bash
npm run test:node
npm run test:python
npm run test:e2e:chat-contract
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
python -m pytest -q tests/runtime
python -m pytest -q tests/contracts
```

Use only the validations relevant to the files you changed. If a validation cannot be run, document why in the PR.

---

## Frontend Runtime Console

The current UI is a cognitive runtime console, not a simple chat window. It exposes:

- chat execution state
- runtime mode
- execution path
- provider diagnostics
- tool diagnostics
- failure class
- debug mode with raw metadata
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

High-level roadmap:

- Phase 1 - Organization
- Phase 2 - Public Debug
- Phase 3 - Execution Recovery
- Phase 4 - Runtime Truth
- Phase 5 - Pipeline Stability
- Phase 6 - Frontend Debug Surface
- Phase 7 - Provider Diagnostics
- Phase 8 - Tool Runtime Reliability
- Phase 9 - Cognitive Decision Quality
- Phase 10 - Controlled Learning Loop

Next focus areas:

- larger decision datasets
- stronger tool/action routing
- better provider fallback behavior
- adaptive routing experiments
- LoRA/model-improvement research
- stricter runtime gates

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

---

## Philosophy

Omni is built on one principle:

> A system is only as good as its ability to explain and improve its own decisions.

The long-term goal is not just better answers. It is a transparent, executable, observable, and evolvable cognitive runtime.

---

## License

See [LICENSE](LICENSE).

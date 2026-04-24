# Omni

Omni is an experimental multi-runtime cognitive system for developer workflows. It combines a Rust API layer, a Python orchestration layer, and a Node/Bun execution layer so a single request can move from chat-style input to planning, tool execution, observability, and controlled fallback.

## What problem Omni tries to solve

Most chatbot-style systems can answer questions, but they are hard to trust when the work needs planning, tools, execution traces, or clear fallback behavior. Omni is trying to solve that by treating a request as an operational runtime flow instead of only a text generation step.

## How Omni works

At a high level:

1. A user request enters through the Rust API.
2. Python coordinates the turn, builds runtime context, and decides what path to use.
3. Node/Bun can provide shortcut responses, execution requests, or action plans.
4. Python can execute runtime actions, synthesize the response, and attach runtime inspection data.
5. Rust returns a stable public response envelope.

## Why Omni is different from a chatbot

Omni is structured as a runtime, not just a prompt wrapper. The repository already includes:

- explicit orchestration in Python
- a separate Node-side execution authority
- Rust transport and API boundaries
- observability and runtime inspection
- governance and control modules
- structured fallback classification

That also means the project is harder to stabilize than a simple chat app, but easier to audit once the runtime paths are working correctly.

## Tech stack

- Rust: API boundary and transport layer
- Python: brain runtime, orchestration, control, observability
- Node.js/Bun: execution authority, planning, execution-request generation
- JSONL/log-based observability and persisted runtime artifacts

## Project status

Omni is currently unstable and under active debugging.

What is already present:

- a real multi-layer runtime architecture
- audit documents for the current runtime behavior
- explicit semantic runtime lanes
- a working `true_action_execution` path in code

What is still not reliable:

- stable end-to-end behavior for every prompt shape
- consistent promotion from planning-only to action execution
- full execution success across all local environments
- clean separation between compatibility mode and the long-term happy path

Start here for the current debugging posture:

- [docs/public-debug/PROJECT_STATUS.md](docs/public-debug/PROJECT_STATUS.md)

## Vision

The goal is to turn Omni into a trustworthy cognitive runtime that can:

- execute real tool-backed workflows
- preserve truth about what actually happened
- expose observable and auditable runtime behavior
- use memory and context in a controlled way
- evolve safely without hiding degraded behavior

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Rust toolchain

### Install

```bash
npm install
```

Python dependencies are currently stdlib-only at the root runtime boundary, but the repository also contains additional requirements files for subprojects such as `backend/python/requirements.txt` and `omni-training/requirements.txt`.

### Useful local commands

Run the Node runtime tests:

```bash
npm run test:node
```

Run the Python tests:

```bash
npm run test:python
```

Run the full test entrypoint:

```bash
npm test
```

Run the Python runtime entrypoint directly:

```bash
python backend/python/main.py
```

Run the Rust API locally:

```bash
cargo run --manifest-path backend/rust/Cargo.toml
```

## Repository guide

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [docs/overview.md](docs/overview.md)
- [docs/architecture/layers.md](docs/architecture/layers.md)
- [docs/architecture/runtime-flow.md](docs/architecture/runtime-flow.md)
- [docs/architecture/runtime-modes.md](docs/architecture/runtime-modes.md)
- [docs/architecture/provider-routing.md](docs/architecture/provider-routing.md)
- [docs/public-debug/REPRODUCTION.md](docs/public-debug/REPRODUCTION.md)
- [ROADMAP.md](ROADMAP.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Contribution entry point

If you want to help, start with:

1. [docs/public-debug/PROJECT_STATUS.md](docs/public-debug/PROJECT_STATUS.md)
2. [CONTRIBUTING.md](CONTRIBUTING.md)
3. [docs/audits/brain-runtime-flow-map.md](docs/audits/brain-runtime-flow-map.md)

This repository is open not because the runtime is finished, but because the current state is valuable to debug in public and improve with evidence.

# 🧠 Omini — Hybrid AI Agent Runtime

> A production-oriented hybrid agent runtime that combines Rust, Python, Node.js, memory, swarm orchestration, and self-evolution into one auditable system.

[![CI](https://img.shields.io/github/actions/workflow/status/YOUR_GITHUB_USER_OR_ORG/omini/ci.yml?branch=main&label=CI)](https://github.com/YOUR_GITHUB_USER_OR_ORG/omini/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20+-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

## What is Omini?

Omini is a hybrid AI agent runtime designed for controlled orchestration rather than opaque monolith behavior. It combines a Python cognitive brain, a Node.js reasoning runner, a Rust subprocess bridge, persistent memory, a multi-agent swarm layer, and a heuristic self-evolution loop. The result is a system that can route work across specialized components, track internal decisions, persist traces, and gradually adjust its behavior without changing the Rust-facing stdout contract.

## Architecture Overview

```text
+-------------------+
|   Web / Mobile    |
+-------------------+
          |
          v
+-------------------+
| Rust HTTP Bridge  |
| Axum API          |
+-------------------+
          |
          v
+-------------------+
| Python Brain      |
| orchestrator.py   |
+-------------------+
          |
          v
+-------------------+
| Swarm Layer       |
| Router / Planner  |
| Executor / Critic |
| Memory            |
+-------------------+
          |
          v
+-------------------+
| Node Runner       |
| THINK -> DECIDE   |
| -> ACT -> MEMORY  |
| -> RESPOND        |
+-------------------+
          |
          v
+-------------------+
| Memory / Sessions |
| Transcripts /     |
| Learning /        |
| Strategy State    |
+-------------------+
```

## Core Components

| Component | Location | Responsibility |
| --- | --- | --- |
| Rust Bridge | `backend/rust` | Exposes HTTP endpoints and calls Python via subprocess while preserving the stdout-only contract |
| Python Brain | `backend/python/brain/runtime` | Owns orchestration, memory loading, transcript/session persistence, and bridge control |
| Capability Registry | `backend/python/brain/registry.py` | Defines capabilities and agent profiles used across the runtime |
| Hybrid Memory | `backend/python/brain/memory` | Persists user data, preferences, notes, learning data, and strategy-linked memory signals |
| Swarm Layer | `backend/python/brain/swarm` | Routes tasks across specialized internal agents and records agent traces |
| Evolution Layer | `backend/python/brain/evolution` | Scores responses, finds patterns, versions strategy updates, and supports rollback |
| Node Runner | `js-runner/queryEngineRunner.js` | Validates the Python-to-Node payload contract and loads the reasoning adapter |
| Reasoning Adapter | `src/queryEngineRunnerAdapter.js` | Implements the cognitive pipeline and delegate resolution |
| Contract Schema | `contract/runner-schema.v1.json` | Formal JSON schema for the Python <-> Node payload |
| Deployment Layer | `docker-compose.yml`, `.github/workflows` | Container orchestration and automation for CI and VPS deployment |

## Cognitive Pipeline

Omini uses a deliberately explicit pipeline:

```text
THINK -> DECIDE -> ACT -> MEMORY -> RESPOND
```

- `THINK`: classifies intent, reads memory, inspects recent history, and builds context.
- `DECIDE`: selects a response strategy and confidence level from available capabilities.
- `ACT`: prepares the practical answer path, delegate plan, or execution outline.
- `MEMORY`: stores useful signals about what happened, including traces, evaluations, and usage.
- `RESPOND`: returns the final user-facing text while preserving a clean Rust-compatible output.

## Multi-Agent Swarm

The swarm layer adds internal specialization without external swarm dependencies.

```text
Input
  |
  v
RouterAgent
  |
  v
PlannerAgent
  |
  v
ExecutorAgent(s)
  |
  v
CriticAgent
  |
  v
MemoryAgent
  |
  v
Final response
```

Current swarm agents:

- `RouterAgent`: classifies intent and chooses the internal route.
- `PlannerAgent`: decomposes complex requests into subtasks.
- `ExecutorAgent`: produces task outputs and execution fragments.
- `CriticAgent`: validates response quality before delivery.
- `MemoryAgent`: consolidates memory signals and persists trace metadata.

## Self-Evolution Loop

Omini includes a heuristic self-evolution layer that does not fine-tune models or require GPUs.

```text
Response
  |
  v
Evaluator
  |
  v
Pattern Analyzer
  |
  v
Strategy Updater
  |
  v
Versioned snapshot
  |
  v
Future orchestrator reads strategy_state.json
```

What it currently does:

- scores each response for relevance, coherence, completeness, and efficiency
- records weak and strong patterns from recent sessions
- proposes strategy changes and versions them in snapshots
- supports rollback to previous strategy versions

## Getting Started

### Prerequisites

- Python `3.11+`
- Node.js `20+`
- Rust toolchain
- Docker and Docker Compose

### Installation

```bash
git clone <your-repo-url>
cd omini
cp .env.example .env
```

Install Node dependencies:

```bash
npm install
```

### Running locally

Run the Python brain:

```bash
cd backend/python
python main.py "hello"
```

Run the Rust bridge:

```bash
cd backend/rust
cargo run
```

Run the Node health command:

```bash
npm run health
```

### Running with Docker

```bash
docker compose up -d --build
docker compose ps
```

## Environment Variables

| Variable | Layer | Description |
| --- | --- | --- |
| `BASE_DIR` | Shared | Base repository path used by the runtime |
| `PYTHON_BASE_DIR` | Python | Python runtime root |
| `NODE_RUNNER_BASE_DIR` | Node | Base directory used by the runner |
| `APP_HOST` | Rust | Host for the Rust API |
| `APP_PORT` | Rust | Port for the Rust API |
| `PYTHON_BIN` | Rust | Python executable used by the Rust bridge |
| `PYTHON_ENTRY` | Rust | Python entrypoint path used by the bridge |
| `MOCK_CHAT` | Rust | Optional fallback mode for the Rust API |
| `AI_SESSION_ID` | Python | Session identifier for runtime persistence |
| `MEMORY_JSON_PATH` | Python | Structured memory store path |
| `MEMORY_DIR` | Python | Hybrid memory directory |
| `TRANSCRIPTS_DIR` | Python | Transcript storage directory |
| `SESSIONS_DIR` | Python | Session snapshot directory |
| `NODE_BIN` | Python | Node executable used by the Python orchestrator |
| `RUNNER_SCHEMA_PATH` | Node | JSON schema path for payload validation |
| `RUNNER_ADAPTER_PATH` | Node | Adapter path used by the runner |
| `SERVER_IP` | Deploy | VPS address used by GitHub Actions deploy |
| `SERVER_USER` | Deploy | SSH user used for deploy |
| `SSH_PRIVATE_KEY` | Deploy | SSH private key stored as a GitHub secret |

## Project Structure

```text
.
├── .github/                     # GitHub workflows, issue templates, PR template, CODEOWNERS
├── backend/
│   ├── python/
│   │   ├── brain/
│   │   │   ├── evolution/       # Scoring, analysis, strategy snapshots, dashboard
│   │   │   ├── memory/          # Hybrid memory primitives and storage helpers
│   │   │   ├── runtime/         # Main orchestrator, sessions, transcripts, swarm logs
│   │   │   └── swarm/           # Internal specialized agents and swarm orchestration
│   │   ├── memory/              # User-facing persisted memory artifacts
│   │   ├── transcripts/         # Session transcript files
│   │   ├── main.py              # Python entrypoint used by the Rust bridge
│   │   └── Dockerfile           # Python production image
│   └── rust/
│       └── src/                 # Axum bridge and subprocess integration
├── contract/                    # Formal payload schemas between runtime layers
├── frontend/                    # Web and mobile frontends
├── js-runner/                   # Node runtime entrypoint and health checks
├── scripts/                     # Server and deployment setup scripts
├── src/                         # Node reasoning adapter
├── docker-compose.yml           # Local and server orchestration
├── ARCHITECTURE.md              # Detailed technical architecture
├── CONTRIBUTING.md              # Development workflow and contribution guide
├── CHANGELOG.md                 # Project release history
└── LICENSE                      # License file
```

## Roadmap

- Improve evaluator heuristics to better separate weak routing from weak answer content
- Add focused test coverage for orchestrator, swarm, and evolution logic
- Expand frontend observability for internal traces in a debug mode
- Add richer capability weighting and intent-specific routing policies
- Introduce safer production-facing health and metrics endpoints

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for local setup, commit conventions, PR rules, and how to extend agents and capabilities.

## License

This project is released under the [MIT License](./LICENSE).

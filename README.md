# Projeto Omni — Cognitive Runtime

A production-oriented **cognitive runtime**: Python orchestration, hybrid memory, specialists and simulation, a Node.js reasoning runner, a Rust HTTP bridge, and explicit **governance** and **observability** layers. Omni is not a single chatbot endpoint—it is a structured system for routed execution, persisted traces, and operator-visible control state.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20+-339933?logo=node.js&logoColor=white)](https://nodejs.org/)

## Overview

Omni combines:

- A **Python brain** (`backend/python/brain`) with `BrainOrchestrator`, planning, continuation, learning, evolution, and **runtime control** (`RunRegistry`, governance controller).
- **OIL (Omni Internal Language)** — typed request/result envelopes, protocol builders, input interpretation, and **output composition** for structured runtime I/O.
- A **governance control plane** — taxonomy (reason / source / severity), per-run `governance_timeline`, `GovernanceResolutionController`, and an **operational read layer** (`operational_governance` summaries).
- **Observability** — read models over goals, traces, simulations, engine adoption, and consolidated governance snapshots for CLI/API consumers.
- **Rust** and **Node** boundaries for HTTP, subprocess execution, and schema-validated runner payloads.

## Architecture (layered)

### OIL — language layer

Location: `backend/python/brain/runtime/language/`

- **Schema**: `OILRequest`, `OILResult`, `OILError` (`oil_schema.py`).
- **Protocol**: handoff builders, legacy adapters (`protocol.py`).
- **Input**: `InputInterpreter`, `interpret_input`, normalizers and intent registry.
- **Output**: `OutputComposer`, `compose_output`, renderers and envelopes.
- Public exports: `brain.runtime.language` (`__init__.py`), including `OMNI_OIL_PROGRAM_RANGE` as a version band label.

### Runtime — execution

Location: `backend/python/brain/runtime/`

- **`orchestrator.py`**: `BrainOrchestrator` coordinates planning, trusted execution, specialists, simulation, checkpoints, and run lifecycle side-effects.
- **Planning / continuation / learning / evolution** under `planning/`, `continuation/`, `learning/`, `evolution/`.
- **Specialists** (`specialists/`), **simulation** (`simulation/`), **goals** (`goals/`), **memory** integrations (`memory/` under runtime and `brain/memory/`).
- **JS / Rust bridges**: `js_runtime_adapter.py`, `rust_executor_bridge.py`.

### Governance control plane

Location: `backend/python/brain/runtime/control/`

- **`RunRegistry`**: source of truth for runs (`run_registry.json` under `.logs/fusion-runtime/control/`), resolution history, and persisted `governance_timeline`.
- **`governance_taxonomy.py`**: canonical governance reason, source, severity, and helpers such as `build_governance_decision`, `governance_dict_for_resolution`.
- **`governance_timeline.py`**: normalized timeline events aligned with the taxonomy.
- **`GovernanceResolutionController`**: canonical transitions into registry updates (orchestrator and CLI use this path where wired).
- **`governance_read_model.py`**: operational views—per-run governance view, waiting/rollback/policy lists, operator-attention ordering, `build_operational_governance_snapshot`.
- **`program_closure.py`**: shared taxonomy version, empty read fallbacks, and shape validation for the operational snapshot contract (Phase 30.9 closure).
- **CLI**: `control/cli.py` — inspect runs, resolution summary, `governance_operational` / `governance_snapshot`, `governance_attention`, operator pause/resume/approve.

### Observability / read layer

Location: `backend/python/brain/runtime/observability/`

- **`ObservabilityReader`**: builds `ObservabilitySnapshot` (goals, traces, simulations, timeline, **governance_summary**, **operational_governance**, recent governance timeline events, **latest_governance_event_by_run**, etc.).
- **`run_reader.py`**: filesystem-backed reads (`read_run`, `read_operational_governance`, …) over `RunRegistry`.

## Execution flow (pipeline)

End-to-end data flow at a high level:

```text
User Input
  → OILRequest (schema + protocol / interpreter path as applicable)
  → Runtime (BrainOrchestrator + planning / execution / specialists)
  → GovernanceResolutionController (governance-aware transitions into RunRegistry)
  → OILResult
  → Output Composer (compose_output / renderers)
  → Natural Response (user-facing text; Rust-facing contracts preserved where applicable)
```

Run persistence and audit trail:

- Resolution transitions append to **`governance_timeline`** and **`resolution_history`** (caps enforced in registry).
- **Operational governance** read surfaces aggregate counts, waiting/rollback/policy runs, and operator-attention ordering for operations.

## Project structure (representative)

```text
.
├── .github/                    # CI workflows, templates
├── backend/
│   ├── python/
│   │   ├── brain/
│   │   │   ├── runtime/        # Orchestrator, OIL, control, observability, planning, …
│   │   │   ├── memory/         # Memory primitives and hybrid helpers
│   │   │   ├── evolution/      # Strategy evolution and evaluation
│   │   │   └── swarm/          # Internal swarm orchestration
│   │   ├── memory/             # Persisted memory artifacts (runtime-adjacent)
│   │   ├── transcripts/
│   │   └── main.py             # Python entrypoint (used by Rust bridge)
│   └── rust/                   # Axum API, subprocess bridge to Python
├── contract/                   # JSON schemas (e.g. runner contract)
├── frontend/                   # Web UI (incl. observability)
├── js-runner/                  # Node runner entrypoint
├── src/                        # Node adapter / query engine integration
├── scripts/                    # Tooling, launcher, packaging
├── supabase/                   # Migrations / schema (when used)
├── docker-compose.yml
├── ARCHITECTURE.md             # Deeper technical notes (if present)
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## Current state

Working today (non-exhaustive):

- Python orchestration with memory, sessions, transcripts, planning, and tool execution policies.
- OIL types, protocol conversion, input interpretation, and output composition for structured flows.
- **RunRegistry** with governance taxonomy fields on resolution records, **governance_timeline**, registry CLI and tests.
- **GovernanceResolutionController** integrated on primary orchestrator/CLI transition paths (with legacy fallbacks where applicable).
- **Operational governance** snapshot (`build_operational_governance_snapshot`, `read_operational_governance`) and observability **`operational_governance`** field on snapshots.
- Node runner with schema validation; Rust bridge; frontend and optional Supabase-related assets.

Always refer to code and tests under `tests/` for authoritative behavior.

## Runtime Convergence Program (Phases 30.1–30.9)

Closed band: **OIL + governance + control-plane read consistency** through Phase **30.9**.

| Phase | Focus |
| --- | --- |
| 30.1 | OIL core schema (`OILRequest` / `OILResult`, errors) |
| 30.2 | OIL input normalization |
| 30.3 | OIL runtime communication (protocol / envelopes) |
| 30.4 | OIL output composition |
| 30.5 | Unified governance taxonomy (reason / source / severity) |
| 30.6 | Unified governance timeline (`governance_timeline` on runs) |
| 30.7 | Governance resolution controller (`GovernanceResolutionController`) |
| 30.8 | Operational governance read layer (`governance_read_model`, consolidated snapshot) |
| 30.9 | Control plane hardening, contract anchors (`program_closure`), closure tests |

Release marker (when tagged in git): **`v9-runtime-convergence-closed`**.

## Next steps (Phase 31+, high level)

- Extend product/API surfaces that consume **`operational_governance`** without changing core persistence contracts.
- Deeper cognitive or domain-specific phases **after** 30.x remain out of scope for this README; follow `CHANGELOG.md` and issue trackers.

## Technologies

- **Python** 3.11+ (orchestrator, OIL, control, observability, tests).
- **Node.js** 20+ (runner, schema validation, `npm` scripts).
- **Rust** (HTTP bridge, subprocess to Python).
- **Docker** / **docker compose** for local and deployment shapes.
- **Frontend**: Vite/React (see `frontend/`).
- Optional: **Supabase** (`supabase/migrations/`) when deploying with that stack.

## Setup and usage

### Prerequisites

- Python **3.11+**
- Node.js **20+**
- Rust toolchain (for `backend/rust`)
- Docker and Docker Compose (optional)

### Installation

```bash
git clone <your-repository-url>
cd <repository-root>
cp .env.example .env   # if present; configure variables for your environment
```

Install Node dependencies at the repository root:

```bash
npm install
```

### Running locally

Python brain (example):

```bash
cd backend/python
python main.py "hello"
```

Rust bridge:

```bash
cd backend/rust
cargo run
```

Node health:

```bash
npm run health
```

### Docker

```bash
docker compose up -d --build
docker compose ps
```

### Control CLI (governance / runs)

From the Python path, the control CLI module is `brain.runtime.control.cli` (invoked as `control-cli` in tests). Typical JSON-oriented commands include `inspect_run`, `resolution_summary`, `governance_operational` / `governance_snapshot`, and operator `pause` / `resume` / `approve`. Use `--root` pointing at the project root when required.

### Tests

```bash
npm run test:python
# and/or
npm test
```

## Environment variables (representative)

| Variable | Role |
| --- | --- |
| `BASE_DIR` | Repository root for runtime path resolution |
| `PYTHON_BASE_DIR` | Python package root |
| `MEMORY_JSON_PATH`, `MEMORY_DIR` | Memory store locations |
| `TRANSCRIPTS_DIR`, `SESSIONS_DIR` | Transcript and session persistence |
| `NODE_BIN` | Node executable for orchestrator-invoked runner |
| `APP_HOST`, `APP_PORT`, `PYTHON_BIN`, `PYTHON_ENTRY` | Rust bridge ↔ Python |
| Deploy-related SSH / server variables | As used in CI (see `.github/workflows`) |

See `.env.example` for the authoritative list in your checkout.

## Notes and constraints

- **Governance** state is persisted under `.logs/fusion-runtime/control/`; treat that tree as operational data, not hand-edited source.
- **Backward compatibility**: older run rows without full `governance` blocks or `governance_timeline` remain loadable via registry synthesis and read-model fallbacks (`program_closure` empty shapes).
- Badges and upstream URLs in third-party README templates may need updating to match your GitHub org and default branch.

## Author

Projeto Omni — maintained by the repository contributors. See `CONTRIBUTING.md` and git history for attribution.

## License

This project is released under the [MIT License](./LICENSE).

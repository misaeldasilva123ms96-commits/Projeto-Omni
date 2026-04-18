# Omni — Cognitive Runtime System

Omni is a **production-grade cognitive runtime**: governed orchestration, auditable control-plane state, multi-agent coordination, structured memory and reasoning, and **bounded evolution** (Phase 39) with **governed continuous improvement** (Phase 40). It is designed as an industrial runtime, not a single-chatbot demo.

## Current maturity

- **Documented system band:** Phases **31–40** (implemented in `backend/python/brain/runtime/`)
- **Current consolidation point:** **Phase 40** — self-improving cognitive system under explicit simulation, approval, staged rollout, monitoring, and rollback (see `docs/phases/phase-40.md`)

## What Omni provides

- **Governance-first execution** — run registry, taxonomy, policy evaluation, and strict tool governance
- **Layered cognition** — OIL-normalized I/O, reasoning, planning, learning, strategy, performance, coordination, decomposition
- **Controlled evolution** — evidence-linked proposals, validation, optional apply to bounded tuning stores, rollback
- **Improvement orchestration** — Phase 40 pipeline on top of Phase 39 traces; no uncontrolled self-modification
- **Operational observability** — consolidated snapshots and JSONL audit traces for SRE-style inspection

## Documentation map

| Topic | Location |
|--------|----------|
| Documentation hub | [`docs/README.md`](docs/README.md) |
| Architecture (detailed) | [`docs/architecture/`](docs/architecture/) |
| Phases 31–40 + history index | [`docs/phases/README.md`](docs/phases/README.md) |
| Governance deep dive | [`docs/governance/`](docs/governance/) |
| Evolution & improvement | [`docs/evolution/`](docs/evolution/) |
| Operations (tests, logs, env) | [`docs/operations/`](docs/operations/) |
| Setup & contributing | [`docs/setup/`](docs/setup/) |
| Product vision & detailed roadmap | [`docs/product/`](docs/product/) |
| Legacy root markdown archive | [`docs/reports/repository-archive/`](docs/reports/repository-archive/) |

## Repository layout (high level)

- `backend/python/brain/runtime/` — orchestrator, control plane, observability, evolution, improvement, planning, learning, etc.
- `backend/rust/` — API / bridge boundary
- `js-runner/`, `src/` — Node runtime integration
- `tests/` — runtime, control, and integration tests
- `docs/` — **canonical documentation tree**

## Quick links

- Architecture summary: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Roadmap summary: [`ROADMAP.md`](ROADMAP.md)
- Governance rules: [`GOVERNANCE.md`](GOVERNANCE.md)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)

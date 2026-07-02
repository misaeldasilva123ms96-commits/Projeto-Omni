# Omni Documentation

This directory is the canonical home for Omni documentation. The repository root keeps short public entrypoints; detailed runtime, architecture, governance, audit, training, release, and product material lives here.

Use this index to avoid stale or duplicated project narratives.

---

## Start Here

| Need | Path |
| --- | --- |
| Current verified repository state | [status/current-state.md](status/current-state.md) |
| Root public README | [../README.md](../README.md) |
| Roadmap and active priorities | [../ROADMAP.md](../ROADMAP.md) |
| Non-negotiable governance rules | [../GOVERNANCE.md](../GOVERNANCE.md) |
| High-level project overview | [overview.md](overview.md) |
| Architecture | [architecture/](architecture/) |
| Runtime providers, BYOK, diagnostics | [runtime/](runtime/) |
| Frontend / Omni Cockpit state | [frontend-current-state.md](frontend-current-state.md), [frontend-omni-cockpit-roadmap.md](frontend-omni-cockpit-roadmap.md) |
| Public debug and reproduction | [public-debug/](public-debug/) |
| Testing and validation | [operations/testing.md](operations/testing.md) |
| Public demo readiness | [release/PUBLIC_DEMO_READINESS.md](release/PUBLIC_DEMO_READINESS.md) |
| Training readiness and safety gates | [training/TRAINING_READINESS.md](training/TRAINING_READINESS.md) |
| Known limitations | [audit/KNOWN_LIMITATIONS.md](audit/KNOWN_LIMITATIONS.md) |
| Product vision and product maturity | [product/vision.md](product/vision.md), [product/roadmap.md](product/roadmap.md) |
| Historical phase material | [phases/README.md](phases/README.md) |
| Research and reference studies | [research/](research/) |
| Setup and contribution details | [setup/](setup/), [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| Archived reports and old root material | [reports/repository-archive/](reports/repository-archive/) |

---

## Current Documentation Model

The docs should be organized around these canonical layers:

1. **Public entrypoints** — `README.md`, `ROADMAP.md`, `GOVERNANCE.md`, `CONTRIBUTING.md`.
2. **Current state** — `docs/status/current-state.md` and focused audit/current-state docs.
3. **Architecture** — runtime flow, layers, bridge contracts, provider routing, tool runtime, learning loop.
4. **Runtime operations** — providers, BYOK, diagnostics, testing, public demo readiness.
5. **Frontend / Cockpit** — current UI state, cockpit roadmap, runtime inspector contracts, observability UX.
6. **Governance and safety** — deny-by-default controls, public-safe payloads, limitations, training gates.
7. **Research and roadmap** — ADRs, reference studies, future plans, product maturity.
8. **Archive** — old reports and superseded material retained for history, not as current truth.

When docs disagree, prefer this order of authority:

1. Current implementation and merged PR evidence.
2. `docs/status/current-state.md`.
3. Root `README.md`, `ROADMAP.md`, and `GOVERNANCE.md`.
4. Focused architecture/runtime/frontend docs.
5. Historical phase reports and archived documents.

---

## Current State Summary

Omni currently includes:

- Rust API boundary and Python Brain subprocess orchestration.
- Node QueryEngine runner and provider/tool execution foundations.
- Runtime Truth metadata and bridge response contracts.
- Provider Auto Routing foundation and Runtime Inspector visibility.
- Governed Token Compression foundation.
- Provider Quota & Cost Dashboard foundation.
- Governed Agent Gateway foundation with sensitive capabilities denied by default.
- Omni Cockpit frontend with runtime, provider, observability, governance, memory, agents, projects, token usage, and lab surfaces.
- Learning records and advisory improvement signals, without automatic self-rewrite.

Omni remains a controlled-demo/research system. Do not document it as production-ready.

---

## Root Files

The root should stay minimal and professional:

- `README.md` — public positioning, architecture summary, getting started, and navigation.
- `ROADMAP.md` — current roadmap/status index and active priorities.
- `GOVERNANCE.md` — non-negotiable governance, compliance, and merge rules.
- `CONTRIBUTING.md` — contributor setup and PR expectations.
- `CHANGELOG.md` — release/change history.
- `LICENSE` — license.

Avoid adding large reports or phase notes to the root. Put detailed material under `docs/`.

---

## Documentation Rules

- Do not claim production readiness.
- Do not claim full cognitive execution without runtime truth evidence.
- Do not treat fallback, matcher, degraded, or compatibility paths as successful full runtime execution.
- Do not document sensitive or unsupported flows as accepted implementation patterns.
- Do not expose secrets, env values, raw payloads, stack traces, headers, API keys, tokens, cookies, private memory stores, or real user conversations.
- Keep OmniRoute and similar external projects as architectural references only unless a future PR explicitly and safely changes that boundary.
- Update docs whenever runtime contracts, provider behavior, frontend runtime surfaces, governance rules, or repository structure change.

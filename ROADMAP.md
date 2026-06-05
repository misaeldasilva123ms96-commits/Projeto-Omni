# Omni Roadmap And Status Index

This file is the repository-level roadmap index. It replaces the older single-track phase list with the current documentation model verified during the runtime audit.

Omni currently has three roadmap tracks:

| Track | Purpose | Primary docs |
| --- | --- | --- |
| Public debug and runtime truth | Make execution paths, fallback, matcher shortcuts, bridge failures, and public diagnostics inspectable. | `docs/public-debug/`, `docs/architecture/runtime-modes.md`, `docs/architecture/bridge-response-contract.md` |
| Security remediation and hardening | Shell/tool governance, payload sanitization, learning redaction, public demo controls, training gates, and audit evidence. | `docs/audit/`, `docs/release/PUBLIC_DEMO_READINESS.md`, `docs/training/TRAINING_READINESS.md` |
| Product maturity | Long-term governed self-improvement and product architecture phases. | `docs/product/roadmap.md`, `docs/phases/` |

## Current Verified State

### Backend / Runtime
- Branch audited: `validation/rust-run-control-fix`
- Commit audited: `9a6c527254fd01f6f07e9f9990b2156c07f34934`
- Default runtime path: Rust/Axum HTTP API -> Python subprocess `BrainOrchestrator` -> Node subprocess QueryEngine runner -> sanitized Python/Rust public response
- Service modes: present but opt-in; subprocess mode remains the default contributor and controlled-demo path
- Readiness: controlled-demo/research-ready, not production-ready

### Frontend (Omni Cockpit Audit) — COMPLETED ✅
- **Branches merged:** All 19 phase branches consolidated into `ui/lab-mode` → `ui/omni-cockpit-audit` → `main` (PRs #294, #295)
- **Tests:** 42 suites, 370 tests — all passing
- **TypeScript:** 0 errors (TS 6.0.3)
- **Coverage:** Design System, Omni Shell, Runtime Truth, Runtime Inspector, Safe Debug, Chat v2, History v2, Provider Center, Token Usage, Projects CRUD, Governance, Memory, Agents, Lab Mode, Mobile, Accessibility, Product Polish
- **Readiness:** Build, typecheck, and test suite all pass clean

## Current Priorities

| Priority | Workstream | Status |
| --- | --- | --- |
| P0 | Keep runtime truth evidence-based. | Implemented and tested; docs must continue to distinguish transport success from cognitive success. |
| P0 | Keep public demo controls honest. | Static validators and security regression tests pass; Docker runtime validation must be checked in the target environment before sharing a public URL. |
| P0 | Keep docs synchronized with implementation. | This index is the current root entrypoint for roadmap/status navigation. |
| P0 | Frontend cockpit audit maintenance. | All 19 phases merged to main; keep tests passing and docs in sync. |
| P1 | Broaden integration confidence. | Local Rust/Python/JS/security suites pass; live HTTP E2E is environment-gated. |
| P1 | Continue hardening service modes. | Python/Node service modes and circuit-breaker behavior exist behind configuration, but are not the default public-demo path. |
| P2 | Expand cognitive evaluation datasets. | Training export remains gated and dry-run; runtime success is not automatically a positive training candidate. |

## What This Roadmap Does Not Claim

- It does not claim Omni is production-ready.
- It does not claim every HTTP 200, valid JSON payload, `status=success`, or `NODE_EXECUTION_SUCCESS` is a full cognitive execution.
- It does not claim fallback, matcher, local/direct, or compatibility paths are positive training examples.
- It does not authorize automatic merge, release tagging, deployment, or training runs.

## Where To Read Next

- Current runtime modes: `docs/architecture/runtime-modes.md`
- Bridge/public response contract: `docs/architecture/bridge-response-contract.md`
- Testing matrix: `docs/operations/testing.md`
- Public demo readiness: `docs/release/PUBLIC_DEMO_READINESS.md`
- Training readiness: `docs/training/TRAINING_READINESS.md`
- Known limitations: `docs/audit/KNOWN_LIMITATIONS.md`
- Detailed product maturity roadmap: `docs/product/roadmap.md`

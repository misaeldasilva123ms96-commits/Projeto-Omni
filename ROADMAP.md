# Omni Roadmap And Status Index

This file is the repository-level roadmap and status index. It keeps the public project narrative aligned with the current audited state of the repository.

Omni is a governed cognitive runtime under active development. It is functional in multiple core paths, but it remains a controlled-demo/research system and must not be documented as production-ready autonomous infrastructure.

---

## Current Verified State

| Area | Current state |
| --- | --- |
| Runtime boundary | Rust/Axum HTTP API with Python Brain subprocess orchestration and Node QueryEngine runner execution. |
| Runtime truth | Evidence-based runtime metadata distinguishes full cognitive execution, partial execution, matcher shortcuts, rule-based intent, compatibility execution, and safe fallback. |
| Provider layer | Configuration-gated provider adapters with diagnostics, fallback metadata, and auto-routing foundation. |
| Frontend | Omni Cockpit / runtime console with Runtime Truth, Runtime Inspector, observability, provider center, governance, memory, agents, projects, token usage, and lab surfaces. |
| BYOK | Session-only BYOK boundary and fail-closed policy remain the documented safety posture. |
| Training | Dry-run / safety-gated training readiness only. Runtime success is not automatically a positive training candidate. |
| Governance | Sensitive capabilities remain deny-by-default. Main merge remains manual. |

Default controlled-demo path:

```txt
Rust/Axum HTTP API
  -> Python subprocess BrainOrchestrator
  -> Node subprocess QueryEngine runner
  -> Python public payload sanitization
  -> Rust HTTP response
```

Service modes can exist behind configuration, but subprocess mode is the default contributor and controlled-demo path unless a future audited change states otherwise.

---

## Recently Merged Current-State Cycle

The latest verified cycle is PR #490 through PR #496:

| PR | Status | Result |
| --- | --- | --- |
| #490 | Merged | Read-only OmniRoute architectural reference study and routing/token-compression ADR context. |
| #491 | Merged | Provider Auto Routing foundation with deterministic auto modes and sanitized runtime truth. |
| #492 | Merged | Runtime Inspector visibility for Provider Auto Routing. |
| #493 | Merged | Governed Token Compression foundation with metadata-only runtime truth and fail-closed controls. |
| #494 | Merged | Provider Quota & Cost Dashboard foundation using safe diagnostics and optional safe metadata. |
| #495 | Merged | Governed Agent Gateway foundation with capability allow-list and sensitive capability deny-by-default behavior. |
| #496 | Merged | Docs-only OmniRoute adaptation-cycle summary and compliance closure. |

### Compliance boundary from this cycle

OmniRoute is only an architectural reference. Omni did not copy OmniRoute code and did not adopt:

- MITM;
- TLS stealth;
- proxy or bypass flows;
- scraping;
- unofficial endpoints;
- sensitive credential import;
- direct OmniRoute integration;
- real MCP/A2A;
- real billing integration;
- real external tool execution for the governed gateway foundation;
- private or unsupported external endpoint flows.

---

## Roadmap Tracks

| Track | Purpose | Primary docs |
| --- | --- | --- |
| Public debug and runtime truth | Keep execution paths, fallback, matcher shortcuts, bridge failures, and diagnostics inspectable. | `docs/public-debug/`, `docs/architecture/runtime-modes.md`, `docs/architecture/bridge-response-contract.md` |
| Runtime and provider reliability | Improve provider routing, provider diagnostics, quota/cost visibility, token handling, and tool execution boundaries without weakening governance. | `docs/runtime/`, `docs/architecture/provider-routing.md`, `docs/research/` |
| Governance and security hardening | Preserve deny-by-default sensitive capabilities, payload sanitization, secret redaction, public-safe diagnostics, and manual merge rules. | `GOVERNANCE.md`, `docs/governance/`, `docs/audit/`, `docs/release/PUBLIC_DEMO_READINESS.md` |
| Omni Cockpit | Keep the frontend aligned with runtime truth, inspector contracts, provider visibility, observability, and safe debug UX. | `docs/frontend-current-state.md`, `docs/frontend-omni-cockpit-roadmap.md`, `frontend/` |
| Training and learning safety | Keep learning records advisory and training export gated by explicit safety readiness. | `docs/training/TRAINING_READINESS.md`, `docs/architecture/learning-loop.md` |
| Product maturity | Long-term governed self-improvement, memory, knowledge, sandbox, agents, and product architecture phases. | `docs/product/roadmap.md`, `docs/phases/` |

---

## Current Priorities

| Priority | Workstream | Status |
| --- | --- | --- |
| P0 | Keep documentation synchronized with real implementation. | Active. README, docs index, roadmap, governance, and current-state docs must be updated after major merges. |
| P0 | Preserve Runtime Truth as the product differentiator. | Implemented foundation. Continue distinguishing transport success from cognitive success. |
| P0 | Preserve compliance boundaries from OmniRoute research. | Documented. Do not introduce MITM, proxy/bypass, scraping, unofficial endpoint, or credential-import flows. |
| P0 | Keep sensitive capabilities deny-by-default. | Governed Agent Gateway foundation added; capability expansion requires scoped tests and docs. |
| P1 | Improve integration confidence across Rust, Python, Node, and frontend. | Continue targeted validation and document skipped environment-specific checks. |
| P1 | Harden opt-in service modes. | Present behind configuration; not the default public/demo path. |
| P1 | Expand Provider Auto Routing safely. | Foundation exists; future work should improve scoring/evidence without hidden provider switching. |
| P1 | Mature token compression. | Foundation exists; future work should stay metadata-safe and fail-closed. |
| P2 | Expand safe evaluation datasets. | Training remains dry-run/safety-gated. |
| P2 | Mature cost/quota visibility. | Dashboard foundation exists; real billing/quota APIs remain out of scope until explicitly designed and governed. |

---

## What This Roadmap Does Not Claim

- It does not claim Omni is production-ready.
- It does not claim every HTTP 200, valid JSON payload, `status=success`, or `NODE_EXECUTION_SUCCESS` is full cognitive execution.
- It does not claim fallback, matcher, local/direct, degraded, or compatibility paths are positive training examples.
- It does not authorize automatic merge, direct main push, release tagging, deployment, billing integrations, credential import, or training runs.
- It does not authorize bypassing external service protections or using private/unofficial endpoints.
- It does not claim real MCP/A2A, real billing, or unrestricted autonomous tool execution is implemented.

---

## Where To Read Next

- Current verified state: `docs/status/current-state.md`
- Documentation index: `docs/README.md`
- Governance rules: `GOVERNANCE.md`
- Current runtime modes: `docs/architecture/runtime-modes.md`
- Bridge/public response contract: `docs/architecture/bridge-response-contract.md`
- Provider routing: `docs/architecture/provider-routing.md`
- Runtime providers/BYOK/diagnostics: `docs/runtime/`
- Frontend current state: `docs/frontend-current-state.md`
- Testing matrix: `docs/operations/testing.md`
- Public demo readiness: `docs/release/PUBLIC_DEMO_READINESS.md`
- Training readiness: `docs/training/TRAINING_READINESS.md`
- Known limitations: `docs/audit/KNOWN_LIMITATIONS.md`
- Detailed product maturity roadmap: `docs/product/roadmap.md`

# Omni Current State

**Date:** 2026-07-02  
**Scope:** public repository documentation state after the merged PR #490-#496 cycle.  
**Status:** controlled-demo/research system, not production-ready autonomous infrastructure.

---

## Executive Summary

Omni is a governed cognitive runtime project. Its current value is not just generating an answer, but exposing what happened during the turn: runtime mode, provider behavior, fallback state, tool execution, governance decisions, diagnostics, and learning signals.

The repository currently has meaningful foundations across backend runtime, provider routing, frontend Cockpit visibility, security/governance, public diagnostics, and documentation. It must still be represented honestly as experimental and evidence-driven.

---

## Current Implemented Foundations

| Area | Current state |
| --- | --- |
| Rust API | HTTP/API boundary, bridge process control, and public response contract. |
| Python Brain runtime | Orchestration, governance, runtime classification, sanitization, and learning signals. |
| Node QueryEngine runtime | Provider routing, tool/action foundations, and execution runner. |
| Runtime Truth | Structured metadata for runtime mode, reason, fallback, provider diagnostics, tool execution, and execution provenance. |
| Provider Auto Routing | Foundation implemented with safe auto modes and runtime truth metadata. |
| Token Compression | Governed foundation with explicit modes and fail-closed safety posture. |
| Quota / Cost visibility | Dashboard foundation using safe diagnostics and optional safe metadata; no real billing API integration. |
| Governed Agent Gateway | Internal foundation with safe capability allow-list and sensitive capabilities denied by default. |
| Frontend / Omni Cockpit | Runtime console with chat, Runtime Truth, inspector, provider center, observability, governance, memory, agents, projects, token usage, and lab surfaces. |
| Learning | Local/advisory improvement signals; no automatic code mutation or uncontrolled self-improvement. |
| Public debug posture | Public-safe diagnostics, known limitations, reproduction docs, and validation scripts. |

---

## Current Default Runtime Path

```txt
Rust/Axum HTTP API
  -> Python subprocess BrainOrchestrator
  -> Node subprocess QueryEngine runner
  -> Python public payload sanitization
  -> Rust HTTP response
```

Python and Node service modes may exist behind configuration, but they are not the default documented contributor path unless a later audited change updates this status.

---

## Recently Merged Cycle: #490-#496

| PR | Result |
| --- | --- |
| #490 | Added a read-only OmniRoute architectural reference study and proposed ADR context. |
| #491 | Added Provider Auto Routing foundation. |
| #492 | Exposed Provider Auto Routing in the Runtime Inspector. |
| #493 | Added Governed Token Compression foundation. |
| #494 | Added Provider Quota & Cost Dashboard foundation. |
| #495 | Added Governed Agent Gateway foundation. |
| #496 | Added OmniRoute adaptation-cycle summary and compliance closure. |

This cycle moved Omni closer to a governed platform with provider routing, compression, usage visibility, and agent-gateway foundations, while preserving strict compliance boundaries.

---

## Compliance Boundaries

The current repository state explicitly does **not** include or authorize:

- OmniRoute code copying;
- direct OmniRoute integration;
- MITM;
- TLS stealth;
- proxy or bypass flows;
- scraping;
- unofficial/private endpoints;
- sensitive credential import;
- real MCP/A2A implementation;
- real provider billing/quota API integrations;
- unrestricted autonomous tool execution;
- automatic main merges;
- direct main pushes;
- uncontrolled self-modification;
- training export without safety gates.

OmniRoute and similar systems may be referenced for architecture research only when documentation preserves these boundaries.

---

## Current Frontend State

The frontend should be described as an **Omni Cockpit / runtime console**, not a simple chatbot UI.

Current frontend surfaces include:

- chat execution surface;
- Runtime Truth topbar;
- Runtime Inspector tabs;
- safe debug presentation;
- provider settings and provider center;
- token usage visibility;
- projects;
- history;
- governance center;
- memory center;
- agents;
- observability;
- lab mode;
- responsive shell and navigation.

The remaining frontend work should focus on contract alignment, data-source clarity, light/dark theme completeness, duplicated provider/settings flows, and end-to-end workflow confidence.

---

## Current Runtime Truth Policy

Transport success is not cognitive success.

A response must not be documented as full cognitive execution only because it returned:

- HTTP 200;
- valid JSON;
- `status=success`;
- `NODE_EXECUTION_SUCCESS`;
- any other successful boundary/transport marker.

Claims about execution quality must inspect runtime mode, provider diagnostics, fallback flags, tool execution, governance state, and provenance.

---

## Current Safety And Training Policy

Learning records and improvement signals are advisory.

Omni does not automatically rewrite itself, mutate runtime behavior, or export positive training examples simply because a response looked successful. Training export remains gated by documented safety criteria, redaction, runtime-mode checks, fallback/tool/governance/provider failure checks, and user-visible success.

---

## Current Priorities

1. Keep README, roadmap, docs index, governance, and status docs synchronized after major merges.
2. Preserve Runtime Truth as the main product differentiator.
3. Strengthen provider routing without hiding fallback or provider failures.
4. Mature token compression while keeping it metadata-safe and fail-closed.
5. Mature quota/cost visibility without adding real billing integrations until explicitly designed.
6. Expand governed agent gateway capabilities only through allowlists, tests, and safe metadata.
7. Improve integration confidence across Rust, Python, Node, and frontend surfaces.
8. Continue frontend Cockpit contract alignment and observability usability.

---

## Documentation Authority

When documents conflict, use this order:

1. Current implementation and merged PR evidence.
2. This file: `docs/status/current-state.md`.
3. Root `README.md`, `ROADMAP.md`, and `GOVERNANCE.md`.
4. Focused architecture/runtime/frontend docs.
5. Historical reports, archived phase notes, and superseded roadmaps.

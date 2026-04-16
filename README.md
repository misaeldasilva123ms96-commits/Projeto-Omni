# Omni — Cognitive Runtime System

Omni is an enterprise-oriented **cognitive runtime**, not a chatbot-only project.  
It provides governed orchestration, auditable control-plane state, bounded evolution workflows, and operational observability across runtime layers.

## Current Status

- **Maturity:** Phase **30.20**
- **Program state:** Runtime governance and controlled self-evolution preparation blocks closed
- **Safety posture:** Governed, bounded, auditable, non-autonomous mutation

## Architecture Overview

Omni follows a layered runtime model:

1. **OIL Layer** — structured runtime input/output contracts and composition
2. **Orchestration Layer** — planning, execution routing, governance-aware control flow
3. **Node Agent Runtime** — JS runner and specialist-oriented execution integration
4. **Memory Layer** — session, transcript, and learning memory surfaces
5. **Evolution Layer** — governed proposal/validation/application/rollback control plane

See `ARCHITECTURE.md` for a deeper layer-by-layer view.

## Core Capabilities

- Governance-first run control (`RunRegistry`, governance taxonomy, timeline, read model)
- Deterministic operational observability (`ObservabilityReader`, governed snapshots)
- Controlled evolution lifecycle:
  - proposal
  - validation
  - explicit review/promotion
  - bounded sandbox application
  - rollback recording
- Cross-runtime execution boundaries (Python orchestrator, Node runtime, Rust bridge)

## Technology Stack

- **Python 3.11+** — cognitive runtime orchestration and control plane
- **Node.js 20+** — agent runtime and JS execution bridge
- **Rust** — HTTP/API boundary and process integration
- **Docker / Compose** — deployment and local parity

## Repository Highlights

- `backend/python/brain/runtime/` — runtime core
- `backend/python/brain/runtime/control/` — governance control plane
- `backend/python/brain/runtime/observability/` — operational read surfaces
- `backend/python/brain/runtime/evolution/` — governed evolution control plane
- `tests/` — runtime, control, observability, contracts

## Roadmap Summary

The current roadmap continues from governance hardening into enterprise closure and next maturity bands.

- **Phase 30:** Runtime governance convergence + controlled evolution preparation (closed at 30.20)
- **Phases 31–40:** Operational scaling, reliability hardening, and enterprise lifecycle maturation

See `ROADMAP.md` for the phase-by-phase structure.

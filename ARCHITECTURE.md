# Architecture (summary)

Omni is a **layered cognitive runtime** with an explicit **control plane** and **read-model observability**. This file is intentionally short; deeper material lives under [`docs/architecture/`](docs/architecture/).

## Control and data flow

```text
Client
  → Rust API boundary
  → Python runtime orchestration (BrainOrchestrator)
  → Node agent runtime (where applicable)
  → Persisted control + memory + audit artifacts
```

## Runtime layers

1. **OIL** — typed runtime I/O contracts (`backend/python/brain/runtime/language/`)
2. **Orchestration** — planning, routing, specialists, continuation (`backend/python/brain/runtime/`)
3. **Node runtime** — JS execution surfaces (`js-runner/`, `src/`, adapters)
4. **Memory** — sessions, transcripts, unified memory (`backend/python/brain/runtime/memory/`)
5. **Evolution (governed)** — proposals, validation, bounded apply, rollback (`backend/python/brain/runtime/evolution/`)
6. **Improvement (Phase 40)** — simulation, approval, staged rollout, monitoring (`backend/python/brain/runtime/improvement/`)

## Governance and observability

- **Governance** — `backend/python/brain/runtime/control/` (taxonomy, run registry, resolution)
- **Observability** — `backend/python/brain/runtime/observability/` (snapshots, JSONL tail readers)

## Further reading

- [docs/architecture/system-overview.md](docs/architecture/system-overview.md)
- [docs/architecture/runtime.md](docs/architecture/runtime.md)
- [docs/architecture/evolution.md](docs/architecture/evolution.md)
- [docs/architecture/improvement-system.md](docs/architecture/improvement-system.md)
- Control layer brief: [docs/architecture/OMNI_COGNITIVE_CONTROL_LAYER.md](docs/architecture/OMNI_COGNITIVE_CONTROL_LAYER.md)

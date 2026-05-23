# Memory architecture

Omni separates **operational memory** (sessions, transcripts, working sets) from **intelligence surfaces** (unified memory layer, hybrid store, learning records). All persistence paths are explicit and inspectable.

## Code map

- `backend/python/brain/runtime/memory/` — runtime memory facade and unified layer
- `backend/python/brain/memory/` — hybrid memory, evidence/decision stores (supporting packages)
- `backend/python/memory/` — durable JSON store paths used by orchestrator configuration

## Observability

Memory intelligence traces are emitted as structured runtime events and appear in `ObservabilityReader` snapshots.

## See also

- [runtime.md](runtime.md)
- Phase 32: `docs/phases/phase-32.md`

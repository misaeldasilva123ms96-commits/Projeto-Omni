# Controlled evolution (Phase 39)

Phase 39 turns runtime evidence into **governed proposals** for safe, reversible **parameter tuning** only. See the authoritative scope document:

- `docs/phases/phase-39.md`

Implementation entrypoint:

- `backend/python/brain/runtime/evolution/controlled_evolution_engine.py`
- `backend/python/brain/runtime/evolution/controlled_apply.py` (`Phase39TuningStore`)

Audit event:

- `runtime.controlled_self_evolution.trace`

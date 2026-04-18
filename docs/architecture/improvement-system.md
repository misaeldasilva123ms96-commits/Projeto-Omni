# Improvement system (Phase 40)

Phase 40 adds **ImprovementOrchestrator**: a governed loop that consumes Phase 39 traces and runtime evidence, simulates impact, enforces approval policy, applies **staged** parameter rollouts, and monitors for regression with rollback.

## Code map

- `backend/python/brain/runtime/improvement/improvement_orchestrator.py`
- `backend/python/brain/runtime/improvement/improvement_simulator.py`
- `backend/python/brain/runtime/improvement/approval_gate.py`
- `backend/python/brain/runtime/improvement/rollout_manager.py`
- `backend/python/brain/runtime/improvement/improvement_pipeline.py`

## Persistence

- Rollout state: `.logs/fusion-runtime/improvement/phase40_rollout.json`
- Applied tuning (shared with Phase 39): `.logs/fusion-runtime/evolution/phase39_tuning.json`

## See also

- `docs/phases/phase-40.md`
- `docs/evolution/improvement-pipeline.md`

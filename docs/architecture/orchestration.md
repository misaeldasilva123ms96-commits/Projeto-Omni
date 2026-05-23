# Orchestration

Orchestration covers **how work is routed**: planning engines, continuation, specialist coordination, execution dispatch, and governance integration — without bypassing the control plane.

## Code map

- `backend/python/brain/runtime/orchestrator.py` — primary user-facing runtime path
- `backend/python/brain/runtime/orchestration/` — orchestration executor and helpers
- `backend/python/brain/runtime/planning/` — planning intelligence
- `backend/python/brain/runtime/continuation/` — continuation decisions
- `backend/python/brain/runtime/specialists/` — specialist coordination surface

## Governance touchpoints

Orchestration respects **run identity**, **policy bundles**, and **governed tools** evaluation before mutating operations. Evolution and improvement layers are **downstream** of execution and learning; they do not replace execution authority.

## See also

- [memory.md](memory.md) — context supplied to orchestration
- [OMNI_COGNITIVE_CONTROL_LAYER.md](OMNI_COGNITIVE_CONTROL_LAYER.md)

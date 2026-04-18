# Observability architecture

Omni exposes a **deterministic read model** over append-only and structured artifacts: execution audit JSONL, governance summaries, traces for reasoning/memory/planning/learning/strategy/performance/coordination/decomposition, controlled evolution, and Phase 40 self-improvement traces.

## Code map

- `backend/python/brain/runtime/observability/observability_reader.py` — snapshot aggregation
- `backend/python/brain/runtime/observability/run_reader.py` — tail readers for audit streams

## Consumers

- Internal tooling / CLI under `brain/runtime/observability/cli.py`
- Operators integrating via stable JSON snapshot shapes

## See also

- [operations/observability.md](../operations/observability.md) — operational usage
- Phase 25 legacy panel notes (archived): `docs/reports/repository-archive/PHASE25_COGNITIVE_OBSERVABILITY_PANEL.md`

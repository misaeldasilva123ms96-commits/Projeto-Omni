# Operations: observability

## Reading snapshots

Use `ObservabilityReader` (`brain/runtime/observability/observability_reader.py`) from a workspace root that contains `.logs/fusion-runtime/`. The snapshot aggregates goals, traces, governance, evolution summaries, and Phase 39–40 traces.

## Audit streams

Primary append-only stream:

- `.logs/fusion-runtime/execution-audit.jsonl`

Event types include `runtime.reasoning.trace`, `runtime.learning_intelligence.trace`, `runtime.controlled_self_evolution.trace`, and `runtime.self_improving_system.trace`.

## See also

- [architecture/observability.md](../architecture/observability.md)

# Runtime architecture

The **Python runtime** under `backend/python/brain/runtime/` is the cognitive control center. `BrainOrchestrator` composes subsystems in a governed order: memory context, reasoning handoff, planning, swarm execution, learning summaries, strategy and performance traces, coordination, task decomposition, then **Phase 39** controlled evolution and **Phase 40** improvement orchestration, emitting structured audit events.

## Key contracts

- **OIL** (`brain/runtime/language/`): normalized requests/results for reasoning and handoff.
- **Execution policy**: governed tools, evidence gates, and strict modes for mutating operations.
- **Persistence**: sessions, transcripts, checkpoints, and `.logs/fusion-runtime/` operational artifacts.

## Phase 39–40 surfaces

- **Controlled evolution**: opportunities → governed proposals → validation → optional apply to `phase39_tuning.json` (parameter-only, reversible). See `docs/phases/phase-39.md`.
- **Improvement orchestration**: simulation → approval → staged rollout → monitoring/rollback. See `docs/phases/phase-40.md` and [improvement-system.md](improvement-system.md).

## See also

- [system-overview.md](system-overview.md)
- [observability.md](observability.md)

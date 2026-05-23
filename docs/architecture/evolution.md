# Evolution architecture

Omni’s evolution stack is **governed**: proposals are explicit objects, validation is mandatory, application is bounded and reversible, and observability records lifecycle state.

## Components

- **Broader evolution registry / services** — `brain/runtime/evolution/` (executor, registry, validation helpers, legacy evolution models) coexist with the Phase 39 narrow path.
- **Phase 39 controlled self-evolution** — `ControlledEvolutionEngine`: bounded opportunity detection, `GovernedProposal` generation, validation, optional apply via `Phase39TuningStore`, monitor/rollback. See `docs/phases/phase-39.md`.

## Non-goals (by design)

- No unconstrained code rewrite from learning signals alone
- No silent cross-cutting mutation outside audited stores

## See also

- [improvement-system.md](improvement-system.md)
- `docs/evolution/controlled-evolution.md`

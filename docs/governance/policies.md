# Policies

## Tooling and execution

- Mutating tools require explicit policy and risk evaluation on the orchestrator path.
- Governed tools strict mode is respected when enabled; engineering tools are allow-listed and audited.

## Evolution and improvement

- Phase 39 applies only **bounded numeric tuning** to `phase39_tuning.json` when explicitly enabled by environment gates.
- Phase 40 requires its own enable/apply/approve gates; when Phase 40 owns apply, controlled evolution defers apply (`skip_apply`) to avoid split authority.

## Documentation discipline

- Long-form documentation belongs under `docs/` by area (see root `GOVERNANCE.md`).

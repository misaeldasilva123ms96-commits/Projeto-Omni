# Operations: runtime behavior

## Notable environment gates (non-exhaustive)

### Phase 39 — controlled evolution

- `OMNI_PHASE39_DISABLE` — disable controlled evolution engine
- `OMNI_PHASE39_APPLY` — allow writes to `phase39_tuning.json` (default off)

### Phase 40 — improvement orchestration

- `OMNI_PHASE40_DISABLE` — hard off
- `OMNI_PHASE40_ENABLE` — enable orchestration; when on, CE uses `skip_apply` so Phase 40 owns apply authority
- `OMNI_PHASE40_APPLY` — allow staged applies after approval
- `OMNI_PHASE40_AUTO_APPROVE` / `OMNI_PHASE40_APPROVE` / `OMNI_PHASE40_FORCE_APPROVE` — approval path (see `docs/phases/phase-40.md`)

## Logs

Runtime artifacts default under `.logs/fusion-runtime/` inside the configured workspace root.

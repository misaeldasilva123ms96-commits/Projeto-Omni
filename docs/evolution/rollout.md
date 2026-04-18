# Rollout (Phase 40)

Rollout is **gradual and deterministic** for integer tuning keys:

1. **Canary** — 25% of the delta from the frozen cycle baseline to the CE target (half-up rounding).
2. **Expanded** — 55% of the same delta.
3. **Full** — apply the CE target value.

State is tracked in `.logs/fusion-runtime/improvement/phase40_rollout.json` including a stable **cycle fingerprint** (`opportunity_id`, tuning key, target) so new CE proposal IDs do not reset an in-flight cycle.

Regression monitoring can trigger **chain rollback** of applied proposal IDs.

See `docs/phases/phase-40.md` for environment gates.

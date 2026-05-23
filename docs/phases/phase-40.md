# Phase 40 — Self-Improving Cognitive System (Governed)

## Scope (implemented)

Phase 40 adds a **governed improvement orchestration layer** downstream of Phase 39 controlled evolution. It does **not** grant open-ended self-modification: it only drives **bounded, validated, staged** application of the same Phase-39 tuning surface (`phase39_tuning.json`).

### Components

- **`ImprovementOrchestrator`** (`brain/runtime/improvement/improvement_orchestrator.py`): `run_cycle(session_id, ce_trace, evidence)` — simulation → approval → **canary (25%) → expanded (55%) → full (100%)** rollout against a stable **cycle fingerprint** (`opportunity_id` + tuning key + target), then monitoring hooks (including monitor-only turns without fresh CE proposals).
- **`improvement_simulator.py`**: deterministic dry-run risk + constraint linkage (reuses Phase 39 `validate_governed_proposal`).
- **`approval_gate.py`**: risk thresholds, optional **auto-approve** for low simulated risk, explicit operator gate via `OMINI_PHASE40_APPROVE`, test-only `OMINI_PHASE40_FORCE_APPROVE`.
- **`rollout_manager.py`**: persists `.logs/fusion-runtime/improvement/phase40_rollout.json` (stage, fingerprint, baseline duration/value, apply ids). **Does not overwrite the final rollout target** with intermediate applied values.
- **`improvement_pipeline.py`**: shared simulation+approval helper and **monitoring snapshot** (duration vs baseline, learning degradation signals).

### Runtime wiring

- After `ControlledEvolutionEngine.evaluate_turn`, the orchestrator always runs `ImprovementOrchestrator.run_cycle` and emits **`runtime.self_improving_system.trace`** with payload `{"trace": ...}`.
- When **`OMINI_PHASE40_ENABLE`** is truthy, CE uses `skip_apply=True` so **Phase 40 owns apply** (Phase 39 `OMINI_PHASE39_APPLY` is bypassed for writes in that mode to avoid double authority).
- Session payload adds **`self_improving_system`** alongside `controlled_self_evolution`.

### Observability

- `read_recent_self_improving_system_traces` / `read_latest_self_improving_system_trace` in `run_reader.py`; mirrored on `ObservabilitySnapshot`.

## Environment gates

- `OMINI_PHASE40_DISABLE=true` — returns a disabled trace; no rollout file mutation beyond reads.
- `OMINI_PHASE40_ENABLE=true` — activates orchestration + defers CE apply as described.
- `OMINI_PHASE40_APPLY=true` — allows physical writes after approval (default remains off).
- `OMINI_PHASE40_AUTO_APPROVE=true` — permits automatic approval when simulated risk ≤ `OMINI_PHASE40_AUTO_APPROVE_MAX_RISK` (default `0.36`).
- `OMINI_PHASE40_APPROVE=true` — explicit operator-style approval when auto path is off.
- `OMINI_PHASE40_FORCE_APPROVE=true` — **tests / emergency only**; bypasses normal gates.

## Governance

- No arbitrary code mutation, no schema breaks, no hidden execution paths.
- Control plane / governance semantics remain authoritative; evolution + improvement remain **audited maintenance** capabilities.

## Beyond Phase 40 (not implemented)

There is **no Phase 41** in this repository scope. Future work (outside this phase) could include richer operator UX, multi-proposal cycles, stronger statistical monitoring, and cross-session promotion policies — still not uncontrolled autonomy.

## Tests

`tests/runtime/improvement/test_improvement_orchestrator.py` covers disable, idle, pending approval, three-stage rollout, and regression rollback.

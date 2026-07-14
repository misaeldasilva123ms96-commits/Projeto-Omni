# Phase 39 — Controlled Self-Evolution Loop

## Scope (implemented)

Phase 39 adds a **strictly bounded, auditable** loop that turns **runtime evidence** (learning, performance, coordination, decomposition, strategy context) into **governed parameter proposals**, validates them, optionally **applies** them to a dedicated tuning file, and supports **monitor + rollback**.

- **`ControlledEvolutionEngine`** (`brain/runtime/evolution/controlled_evolution_engine.py`): per chat turn, after learning — detect → propose (first actionable only) → validate → apply (env-gated) → monitor/rollback when the same stress category reappears under `pending_monitor`.
- **`Phase39TuningStore`** (`controlled_apply.py`): persists `phase39_tuning.json` under `.logs/fusion-runtime/evolution/` with numeric knobs only (no code mutation).
- **Allowed knobs**: `decomposition_max_subtasks` (4–8), `performance_max_cache_entries` (16–128), `strategy_risk_bias`, `coordination_issue_budget`, `observability_tail_lines` — each change is **clamped**, **versioned**, and **rollbackable** via `apply_history`.
- **Runtime wiring**: `BrainOrchestrator.run` reads tuning **before** decomposition/performance; runs evolution **after** learning; emits `runtime.controlled_self_evolution.trace`; stores `controlled_self_evolution` on the session payload.
- **Observability**: `read_recent_controlled_self_evolution_traces` / `read_latest_controlled_self_evolution_trace`; snapshot fields on `ObservabilitySnapshot`.

## Environment gates

- `OMNI_PHASE39_DISABLE=true` — engine returns a disabled trace; no file writes.
- `OMNI_PHASE39_APPLY=true` — validated proposals may be written to the tuning store. **Default is off** (`apply_status=skipped_policy`) so production stays read-only unless explicitly enabled.

The corresponding `OMINI_*` names remain temporary compatibility aliases; canonical `OMNI_*` values take precedence.

## Governance

Evolution **never** bypasses control-plane execution allow/block, does **not** rewrite code or schemas, and does **not** connect learning signals directly to behavior without the proposal + validation + optional apply path.

## Phase 40 (implemented separately)

See `docs/phases/phase-40.md` — governed **continuous improvement orchestration** (simulation, approval, gradual rollout, monitoring) layered on top of Phase 39 proposals. Still **no** uncontrolled code mutation or architecture-wide autonomous refactors.

## Tests

`tests/runtime/evolution/test_controlled_evolution_engine.py` covers disable flag, apply + rollback regression path, and validation rejection.

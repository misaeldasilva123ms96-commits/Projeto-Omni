# Governance Rules

## Core rules

1. **One phase at a time**  
   Changes must be scoped to the active phase objective. No leapfrogging.

2. **Mandatory gates**  
   A phase is only closed after required gates pass with test-backed evidence.

3. **Observability required**  
   New control-plane capabilities must expose operationally readable state.

4. **No uncontrolled evolution**  
   No autonomous approval, no autonomous patch generation/application, no uncontrolled mutation scope.

## Runtime safety principles

- Governance-first transitions over implicit behavior.
- Deterministic validation before any bounded apply path.
- Explicit rollback safety for controlled application attempts.
- Append-only history for auditable lifecycle events.

## Control plane discipline

- Prefer additive contract changes over breaking changes.
- Keep read-model fallbacks stable and explicit.
- Preserve backward compatibility for empty/legacy persisted state when possible.
- Require regression coverage for control-plane updates.

## Documentation discipline

- **No long-form documentation at the repository root** beyond the minimal entrypoints (`README`, `ARCHITECTURE`, `ROADMAP`, `CHANGELOG`, this file).
- **Phases** → `docs/phases/` (with narrative index in `docs/phases/README.md`).
- **Architecture** → `docs/architecture/`.
- **Evolution / improvement** → `docs/evolution/` + `docs/phases/phase-39.md` and `phase-40.md`.
- **Audits / deep-dive analyses** → `docs/reports/audits/` and `docs/reports/analysis/`.
- **Legacy root markdown** → `docs/reports/repository-archive/` (moved, not deleted).

Expanded policy context: [`docs/governance/`](docs/governance/).

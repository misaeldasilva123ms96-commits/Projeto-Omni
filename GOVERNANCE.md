# Governance Rules

## Core Rules

1. **One phase at a time**  
   Changes must be scoped to the active phase objective. No leapfrogging.

2. **Mandatory gates**  
   A phase is only closed after required gates pass with test-backed evidence.

3. **Observability required**  
   New control-plane capabilities must expose operationally readable state.

4. **No uncontrolled evolution**  
   No autonomous approval, no autonomous patch generation/application, no uncontrolled mutation scope.

## Runtime Safety Principles

- Governance-first transitions over implicit behavior.
- Deterministic validation before any bounded apply path.
- Explicit rollback safety for controlled application attempts.
- Append-only history for auditable lifecycle events.

## Control Plane Discipline

- Prefer additive contract changes over breaking changes.
- Keep read-model fallbacks stable and explicit.
- Preserve backward compatibility for empty/legacy persisted state when possible.
- Require regression coverage for control-plane updates.

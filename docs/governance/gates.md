# Gates and closure

Phases close only when **test-backed** and **observability-backed** evidence exists for the scoped change. Runtime changes that touch the control plane require regression coverage for read-model compatibility and deterministic behavior.

## Phase-level gates (pattern)

- Unit tests for new modules (`tests/runtime/...`)
- Integration tests for orchestrator wiring where applicable
- No new silent persistence paths without audit event or structured snapshot support

## Release discipline

- `CHANGELOG.md` records externally visible changes
- CI validates Python and Node surfaces (see repository workflows)

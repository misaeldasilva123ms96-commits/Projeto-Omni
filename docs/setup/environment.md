# Environment configuration

Omni reads environment variables for runtime mode, session identity, workspace roots, and phased feature gates (notably Phase 39–40 evolution/improvement controls).

## Workspace roots

Typical development uses `BASE_DIR` / `PYTHON_BASE_DIR` style variables (see orchestrator integration tests and `BrainPaths`).

## Safety defaults

Governed mutation and evolution **default to off** unless explicitly enabled — production-like setups should keep defaults until operators intentionally opt in.

See also: [../operations/runtime-behavior.md](../operations/runtime-behavior.md).

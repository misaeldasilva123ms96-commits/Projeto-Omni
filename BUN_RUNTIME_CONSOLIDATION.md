# Bun Runtime Consolidation

## Objective

This pre-Phase 22 change makes the Omni JavaScript runtime layer Bun-first while preserving a deterministic fallback to Node.

The scope is intentionally narrow:

- JS runtime tools and adapters prefer Bun when available
- Python subprocess execution is standardized around a shared runtime selector
- frontend and Vite workflows remain Node-compatible and unchanged

## Scope

Affected areas:

- `backend/python/brain/runtime/js_runtime_adapter.py`
- `backend/python/brain/runtime/orchestrator.py`
- `scripts/js-runtime-launcher.mjs`
- `package.json`
- `js-runner/runtimeHealthcheck.js`
- runtime validation tests

Intentionally unchanged:

- frontend package manager strategy
- Rust gateway runtime model
- broader Node-based container defaults
- repo-wide CI/CD assumptions

## Bun-first Strategy

Selection order:

1. `OMINI_JS_RUNTIME_BIN` if explicitly configured
2. Bun via `BUN_BIN` or `bun` on `PATH`
3. Node via `NODE_BIN` or `node` on `PATH`

This means Bun is preferred whenever it is available, but runtime execution does not become Bun-only.

## Node Fallback Strategy

If Bun is unavailable, Omni falls back to Node deterministically.

Fallback metadata is exposed in Python diagnostics through:

- selected runtime name
- selected executable
- selection source
- whether fallback was used

This keeps the existing runtime safe in environments that only have Node.

## Runtime Selection Logic

`JSRuntimeAdapter` is now the Python-side source of truth for JS runtime invocation.

It is responsible for:

- runtime detection
- environment shaping
- command construction
- explicit Bun/Node metadata

`scripts/js-runtime-launcher.mjs` provides the same preference policy for package scripts and local JS-side validation commands.

## Affected Modules and Scripts

### Python

- `backend/python/brain/runtime/js_runtime_adapter.py`
- `backend/python/brain/runtime/orchestrator.py`

### JavaScript

- `scripts/js-runtime-launcher.mjs`
- `js-runner/healthcheck.js`
- `js-runner/runtimeHealthcheck.js`

### Package Scripts

Added or updated:

- `runtime:which`
- `runner`
- `runner:node`
- `runner:bun`
- `health`
- `health:node`
- `health:bun`
- `test:js-runtime`

The general scripts now go through the launcher so local execution can prefer Bun automatically without forcing Bun everywhere.

## Frontend Boundary

The frontend remains intentionally outside this consolidation.

`frontend/package.json` still uses:

- `vite`
- `vite build`
- `vite preview`

No frontend build script was migrated to Bun-only behavior. This keeps Vite workflows stable.

## Env Caveats

Relevant variables:

- `OMINI_JS_RUNTIME_BIN`: explicit runtime override
- `BUN_BIN`: Bun candidate override
- `NODE_BIN`: Node candidate override and fallback path
- `OMINI_JS_RUNTIME`: selected runtime metadata for subprocesses
- `OMINI_JS_RUNTIME_SOURCE`: selection reason metadata
- `NODE_RUNNER_BASE_DIR`: workspace root for the JS runner

Important rule:

- explicit override wins
- otherwise Bun is preferred
- Node remains the compatibility fallback

## Lockfile / Package Manager Decision

This phase keeps the existing repo-wide lockfile strategy.

Decision:

- keep `package-lock.json` as the authoritative repo lockfile
- do not introduce `bun.lock` in this consolidation
- allow Bun to run the JS runtime operationally without forcing a package manager migration

Why:

- it keeps the scope small
- it avoids destabilizing frontend and Docker assumptions
- it preserves current install and CI expectations

## Validation Steps

Suggested validation commands:

- `python -m unittest tests.runtime.test_js_runtime_adapter tests.runtime.test_memory_context_integration tests.runtime.test_control_layer_integration`
- `node tests/runtime/js_runtime_launcher.test.mjs`
- `node tests/runtime/queryengineRunner.integration.test.mjs`
- `node tests/runtime/queryengine.smoke.test.mjs`
- `npm run runtime:which`

## Limitations

- Docker images still default to Node-based installs and execution paths
- Rust health/dependency reporting still uses `NODE_BIN` naming
- Bun is operationally preferred, but not required
- repo-wide package manager migration is intentionally deferred

## Result

Omni now has a bounded Bun-first runtime policy for the JS execution layer without crossing the line into a risky whole-repo migration.

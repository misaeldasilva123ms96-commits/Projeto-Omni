# Operations: Testing

This page documents the current local validation matrix for the audited multi-runtime tree.

Latest audit base used for this update:

- Branch audited: `release/omni-current-state-2026-05-21`
- Base: `origin/main` after PR #171

## Primary Local Matrix

Run from the repository root unless a command states otherwise.

| Command | Coverage | Current audit result |
| --- | --- | --- |
| `cargo test` | Rust/Axum API, request validation, run control, rate limiting, bridge behavior | PASS |
| `npm run test:js-runtime` | Node QueryEngine runner, runtime truth contracts, specialists, Supabase optional dependency handling | PASS |
| `npm run test:python:pytest` | Python runtime pytest suite, observability, governance, learning, training gates | PASS |
| `npm run test:security` | Consolidated security regression suite across hardening phases | PASS |
| `npm run validate:public-demo` | Static public demo readiness validator | PASS |
| `npm run validate:audit-pack` | Static audit-pack validator | PASS |
| `git diff --check` | Whitespace and patch hygiene | Required before commit |

Provider/BYOK focused checks:

```bash
node tests/runtime/providerRouterFallback.test.mjs
node tests/runtime/providerRouterMetadata.test.mjs
node tests/runtime/remoteProviderExecutor.test.mjs
node tests/runtime/runtimeTruthContract.test.mjs
python -m pytest tests/runtime/test_bridge_pipeline.py tests/runtime/test_cognitive_orchestration.py -v
```

## Focused Runtime/Security Commands

Use these for targeted changes:

```bash
python -m pytest -q tests/runtime/observability/test_runtime_truth_contract.py
python -m pytest -q tests/runtime/test_tool_governance_enforcement.py
python -m pytest -q tests/training/test_training_readiness_phase13.py
node tests/runtime/toolGovernanceEnforcement.test.mjs
node tests/runtime/specialistErrorPolicy.test.mjs
node tests/runtime/supabaseClientOptional.test.mjs
```

## Frontend Commands

Frontend validation is useful for UI/debug-surface changes:

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Frontend tests may emit Vite or chart layout warnings. Treat warnings as investigation items when they affect assertions or rendered diagnostics.

## Integration And E2E Notes

- `OMNI_E2E_API_URL` is the canonical live HTTP E2E URL. `OMINI_E2E_API_URL` remains a temporary compatibility alias, with the canonical value taking precedence when both are set.
- `npm run test:e2e:chat-contract` always validates fixtures. Set `OMNI_E2E_REQUIRE_LIVE=true` together with `OMNI_E2E_API_URL` to make an absent, unreachable, non-2xx, degraded, or incomplete Rust → Python → Node → Rust path fail the command.
- `.github/workflows/omni-live-e2e-ci.yml` starts the local Rust API and runs that required live contract on pull requests, `main`, `ci/**`, and manual dispatches. It does not depend on a deployed environment or provider secret.
- `npm run test:integration` is not a current root script in the audited tree.
- `npm run intake:validate` is not a current root script in the audited tree.
- Docker commands require a working local Docker daemon and should not be inferred from static validators alone.

## Docker/Public Demo Validation

Static checks:

```bash
npm run validate:public-demo
docker compose -f docker-compose.demo.yml config
```

Runtime checks, when Docker is available:

```bash
docker build -f Dockerfile.demo -t omni-demo:local-validation .
docker compose -f docker-compose.demo.yml up --build
```

The latest documentation audit verified the static validators, not a fresh Docker image build/runtime smoke in that pass.

## Interpreting Success

Test success and transport success are not the same as cognitive success. HTTP 200, valid JSON, `status=success`, and `NODE_EXECUTION_SUCCESS` mean a boundary returned a usable payload. Runtime correctness must be checked through:

- `cognitive_runtime_inspection`
- `runtime_truth`
- `fallback_triggered`
- provider diagnostics
- tool execution diagnostics
- governance and safety metadata

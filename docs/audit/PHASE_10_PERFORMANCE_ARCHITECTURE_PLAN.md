# PHASE 10 — PERFORMANCE ARCHITECTURE PLAN

Date: 2026-05-01

Base branch: training/readiness-13

Base commit: 0e640f5cf65309505accc33d9b69a511c4eecc37

Working branch: architecture/persistent-runtime-plan-10

## Scope

Planning only. No runtime behavior changed, no API contracts changed, no persistent services implemented, and subprocess mode was not removed.

## Files Changed

- `docs/architecture/persistent-runtime-services-plan.md`
- `docs/audit/PHASE_10_PERFORMANCE_ARCHITECTURE_PLAN.md`

## Inspected Paths

- `backend/rust/src/main.rs`
- `backend/python/main.py`
- `backend/python/brain/runtime/orchestrator.py`
- `js-runner/queryEngineRunner.js`
- `src/queryEngineRunnerAdapter.js`
- `core/brain/queryEngineAuthority.js`
- `Dockerfile.demo`
- `docker-compose.demo.yml`
- `docs/architecture/bridge-pipeline.md`
- `docs/architecture/bridge-response-contract.md`
- `docs/architecture/runtime-modes.md`
- `docs/audit/CODEMAP_REMEDIATION_TARGETS.md`
- `docs/audit/PHASE_2_RUNTIME_TRUTH_CONTRACT.md`
- `docs/audit/PHASE_3_TOOL_GOVERNANCE_ENFORCEMENT.md`
- `docs/audit/PHASE_5_INPUT_VALIDATION_RATE_LIMITING.md`
- `docs/audit/PHASE_6_CONTAINER_PUBLIC_DEMO.md`
- `docs/training/TRAINING_READINESS.md`

## Plan Summary

The plan migrates from subprocess-per-request execution to persistent internal Python and Node services while keeping Rust as the only public API boundary and preserving subprocess compatibility as the default mode.

## Target Services

- Python internal service:
  - `POST /internal/brain/run`
  - `GET /internal/brain/health`
  - `GET /internal/brain/readiness`
- Node internal service:
  - `POST /internal/query-engine/run`
  - `GET /internal/query-engine/health`
  - `GET /internal/query-engine/readiness`

## Feature Flags

- `OMNI_PYTHON_MODE=subprocess|service`
- `OMINI_PYTHON_MODE=subprocess|service`
- `OMNI_NODE_MODE=subprocess|service`
- `OMINI_NODE_MODE=subprocess|service`

Default remains `subprocess`.

## Migration Subphases

- 11A Python service: ~2 weeks
- 11B Node service: ~2 weeks
- 11C Rust internal client: ~1 week
- 11D circuit breaker/fallback: ~1 week
- Total: ~6 weeks

## Compatibility And Rollback

- Subprocess mode remains default.
- Service mode stays behind env flags.
- Old Python stdin runner and Node CLI runner remain available.
- Rollback is env-only initially: set `OMNI_PYTHON_MODE=subprocess` and `OMNI_NODE_MODE=subprocess`.
- No data migration is required initially.

## Security / Observability

The plan preserves:

- Rust public boundary
- input validation and rate limiting
- public demo shell/debug restrictions
- governance-before-tool-execution
- runtime truth classification
- public-safe error taxonomy
- backend/frontend/learning sanitizers
- request ID and latency propagation
- no raw secrets, env, stack, stdout/stderr, command args, provider payloads, tool payloads, or memory contents in public diagnostics

## Validation Results

- `npm run test:security` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `npm test` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `npm run test:js-runtime` — PASS, exit code 0. Local npm wrapper emitted no detailed output in this run.
- `npm --prefix frontend run typecheck` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `node tests/security/security-regression-suite.mjs` — PASS. Consolidated security suite passed.
- `npm run test:python:pytest` — TIMEOUT after 300 seconds.
- `cd backend/rust && cargo test` — PASS. 38 passed; warning remains for unused `InvalidRequest` variant.
- `git diff --check` — PASS.

## Inherited Issues

- `npm run test:python:pytest` broad wrapper timeout repeated and is classified as inherited because this phase changed documentation only and focused/security/Rust validations passed.
- Frontend chart dimension warnings appear in Vitest output from `RuntimePanel` tests and are unrelated to Phase 10 documentation.
- Rust warning for unused `InvalidRequest` variant remains unrelated to Phase 10 documentation.

## Known Limitations

- This phase is documentation only.
- Docker daemon availability remains required to prove future service container builds.
- The plan intentionally does not choose a Python/Node HTTP framework; that belongs to implementation phases 11A/11B.

## Rollback

Revert the Phase 10 commit on `architecture/persistent-runtime-plan-10`.

## Gate 10 Status

Status: PASSED.

Reason: architecture plan exists, migration is incremental, subprocess compatibility and rollback are preserved, estimates are documented, validation was attempted, and no runtime behavior changed.

## No Merge Into Main

This phase does not merge into main.

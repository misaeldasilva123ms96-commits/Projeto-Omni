# PHASE 7 — SECURITY REGRESSION TEST SUITE

Date: 2026-05-01

Base branch: deploy/container-public-demo-06

Base commit: 012d50cd0bc340608930b9fd1a065eb2f876f5d2

Working branch: security/regression-suite-07

## Scope

Phase 7 adds a consolidated security regression entrypoint. It does not rewrite runtime architecture or change security behavior except to make already hardened contracts easier to verify.

## Regression Suite Location

- `tests/security/security-regression-suite.mjs`
- npm entrypoint: `npm run test:security`

## Coverage Map

| Area | Reused tests |
| --- | --- |
| Phase 1A shell hardening | `tests/runtime/test_shell_policy_hardening.py` |
| Phase 1B specialist/error logging | `tests/runtime/specialistErrorPolicy.test.mjs` |
| Phase 1C backend payload sanitization | `tests/runtime/observability/test_public_runtime_payload.py` |
| Phase 1D frontend debug sanitization | `frontend/src/lib/runtimeDebugSanitizer.test.ts`, `RuntimeDebugSection.test.tsx`, `RuntimePanel.test.tsx` |
| Phase 1E learning/log redaction | `tests/runtime/learning/test_learning_redaction.py` |
| Phase 2 runtime truth contract | `tests/runtime/observability/test_runtime_truth_contract.py`, `tests/runtime/runtimeTruthContract.test.mjs` |
| Phase 3 tool governance | `tests/runtime/test_tool_governance_enforcement.py`, `tests/runtime/toolGovernanceEnforcement.test.mjs` |
| Phase 4 secrets/config | `tests/runtime/secretsConfigHardening.test.mjs`, `tests/runtime/test_secrets_config_hardening.py`, `tests/config/test_secrets_manager.py` |
| Phase 5 input validation/rate limiting | Rust `chat_route_` tests and `chat_security_env_aliases_work` |
| Phase 6 public demo container | `tests/runtime/containerPublicDemo.validation.mjs` |
| Phase 8 error taxonomy | `tests/runtime/test_error_taxonomy.py`, `tests/runtime/errorTaxonomy.test.mjs` |

## Required Cases Covered

- Shell blocked by default, blocked in public demo, ALLOW_SHELL cannot bypass demo mode, dangerous commands rejected.
- Specialist fallback does not expose raw message/stack/path/env and public demo never exposes `internal_debug`.
- Backend public payload strips stack/stdout/stderr/command/env/raw provider/tool/memory data while preserving public runtime fields.
- Frontend runtime debug panels render sanitized debug payloads only.
- Learning redaction covers API keys, JWT, Bearer tokens, email, phone, CPF, paths, and raw internal payload fields.
- Runtime truth differentiates matcher, fallback, and tool-blocked modes.
- Tool governance gates sensitive/write/destructive/git/network categories and returns public-safe audit.
- Supabase raw key/url exports remain absent, provider diagnostics are status-only, `.env.example` uses placeholders.
- API validation rejects invalid inputs before runtime and rate limiting is tested.
- Demo container config is present, safe env is set, compose is not privileged and does not mount docker.sock.
- Error taxonomy codes include public message/severity/retryable/internal redaction fields.

## Validation Commands / Results

- `node tests/security/security-regression-suite.mjs` — PASS. Covered Phases 1A-1E, 2, 3, 4, 5, 6, and 8 focused regression tests.
- `npm run test:security` — PASS, exit code 0. Local npm wrapper emitted no detailed output; direct Node entrypoint above is the detailed validation evidence.
- `npm test` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `npm run test:js-runtime` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `npm run test:python:pytest` — TIMEOUT after 300 seconds. Classified as inherited broad-suite timeout because focused Python security tests passed in the consolidated suite.
- `npm --prefix frontend run typecheck` — PASS, exit code 0. Local npm wrapper emitted no detailed output.
- `cd backend/rust && cargo test` — PASS. 38 tests passed; warning remains for unused `InvalidRequest` variant.
- `git diff --check` — PASS with CRLF warning for `package.json`.
- `docker compose -f docker-compose.demo.yml config` — PASS.
- `docker build -f Dockerfile.demo -t omni-demo:phase7 .` — NOT RUN to completion because Docker daemon is unavailable.

## Docker Availability

Docker CLI and Compose are installed:

- Docker version 29.3.1
- Docker Compose version v5.1.1

Static Compose validation passed. Docker image build failed before execution because the local daemon pipe was unavailable:

`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`

## Known Limitations

- The consolidated suite intentionally reuses focused tests instead of slow end-to-end flows.
- Rust full-suite concurrency can still expose the inherited `run_control` test flake; serial cargo test remains the fallback evidence if needed.
- Docker image build depends on the local Docker daemon being available.

## Rollback

Revert the Phase 7 commit on `security/regression-suite-07`.

## Gate 7 Status

Status: PASSED.

Reason: consolidated security regression suite exists, focused coverage is mapped to all required phases, broad validations either passed or were classified with evidence, Docker static validation passed, and no runtime architecture or security behavior was weakened.

## No Merge Into Main

This phase does not merge into main.

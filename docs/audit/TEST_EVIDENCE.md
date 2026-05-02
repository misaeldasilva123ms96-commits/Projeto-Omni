# Test Evidence

## Command Matrix

| Command | Purpose | Latest Phase 14/15 status |
| --- | --- | --- |
| `npm run validate:audit-pack` | Audit pack static validation | Added in Phase 15 |
| `npm run validate:public-demo` | Public demo static validation | Passed in Phase 14 |
| `npm run test:security` | Consolidated security regression suite | Passed in Phase 14 |
| `npm test` | Node runtime plus Python unittest wrapper | Passed in Phase 14 |
| `npm run test:js-runtime` | JS/Node runtime tests | Passed in Phase 14 |
| `npm run test:python:pytest` | Focused Python pytest suite | Passed in Phase 14 |
| `npm --prefix frontend run typecheck` | Frontend TypeScript check | Passed in Phase 14 |
| `cd backend/rust && cargo test` | Rust API/runtime tests | Passed in Phase 14 rerun |
| `python -m py_compile backend/python/brain_service.py backend/python/main.py` | Python syntax check | Passed in Phase 14 |
| `docker compose -f docker-compose.demo.yml config` | Compose static validation | Passed in Phase 14 |
| `docker build -f Dockerfile.demo -t omni-demo:phase14 .` | Demo image build | Blocked by unavailable local Docker daemon |
| `git diff --check` | Whitespace/diff validation | Passed with Windows CRLF warnings |

## Tests Passed By Phase

- Phase 1A-1E: shell, logging, backend payload, frontend debug, and learning redaction tests were added and covered by security regression.
- Phase 2: runtime truth Python/JS contract tests were added.
- Phase 3: governance enforcement tests were added.
- Phase 4: secrets/config tests were added.
- Phase 5: Rust `/chat` validation and rate limit tests were added.
- Phase 6: container static validation was added.
- Phase 7: consolidated security regression suite was added.
- Phase 8: public error taxonomy tests were added.
- Phase 9: learning safety tests were added.
- Phase 10: documentation-only validation was run.
- Phase 11A-11D: Python service, Node service, Rust client, and circuit breaker tests were added.
- Phase 12: intent classifier tests and eval harness were added.
- Phase 13: training candidate validation/export tests were added.
- Phase 14: public demo readiness validation was added.

## Docker Status

Compose config validation passed. Docker image build still needs daemon-backed validation before public demo exposure. The local Phase 14 attempt failed because Docker Desktop Linux engine was not available at the configured named pipe.

## Security Regression Suite Status

`npm run test:security` passed in Phase 14 and remains the required consolidated gate before public demo.

## Public Demo Validation Status

`npm run validate:public-demo` passed in Phase 14. It checks required files, demo env, disabled shell/debug, enabled rate limiting, Docker/compose hardening, `.dockerignore`, and obvious secret patterns.

## Rust Python JS Frontend Status

Rust, Python, JS runtime, security, and frontend typecheck commands passed in Phase 14 after rerun. Final Phase 15 validation reruns these commands and records any updated failures in `PHASE_15_AUDIT_PACK_RELEASE_GATE.md`.

## Known Timeouts Or Flakes

One Phase 14 `cargo test` attempt transiently failed two `run_control` tests with HTTP 500. A serial rerun passed 46 tests, and a normal rerun also passed 46 tests. No Rust code was changed in Phase 14.

## Non-Blocking Issues

- Docker image build is required before public demo because the local daemon was unavailable.
- `git diff --check` may report CRLF warnings on Windows; no whitespace errors were reported.

## Phase 15 Evidence Update

Passed in Phase 15:

- `npm run validate:audit-pack`
- `npm run validate:public-demo`
- `npm run test:security`
- `npm test`
- `npm run test:js-runtime`
- `npm run test:python:pytest`
- `npm --prefix frontend run typecheck`
- `python -m py_compile backend/python/brain_service.py backend/python/main.py`
- `docker compose -f docker-compose.demo.yml config`
- `git diff --check`

Phase 15 non-blocking environment issues:

- `cargo test` repeated the known `run_control` flake once with 44 passed and 2 failed.
- Serial Rust rerun timed out after local Docker/build operations saturated the shell.
- Docker image build timed out after 907 seconds and remains required before public demo.

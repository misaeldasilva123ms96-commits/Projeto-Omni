# POST-ROADMAP DOCKER DEMO VALIDATION

Branch: `validation/docker-demo-build-smoke`

Base branch: `release/audit-pack-15`

Base commit: `e2d7933f459794e4ee5ae0f9b4989772957006b9`

Statement: post-roadmap validation only. No merge into main, no release tag, no public deployment, no training run.

## Docker Daemon Status

Passed:

- `docker --version`: Docker version 29.4.1, build 055a478
- `docker compose version`: Docker Compose version v5.1.3

## Compose Config Result

Passed:

```bash
docker compose -f docker-compose.demo.yml config
```

Confirmed:

- public demo env enabled
- shell/debug disabled
- rate limiting enabled
- Python/Node subprocess modes
- read-only compose filesystem
- no-new-privileges
- cap_drop ALL
- no docker.sock mount

## Docker Build Result

Initial build before fixes:

- `docker build -f Dockerfile.demo -t omni-demo:validation .` passed.
- Image tag: `omni-demo:validation`
- Slow layer: final `chown -R omni:omni /app /opt/venv` took about 920 seconds.

Initial container start failed:

```txt
observability auth configuration failed error=missing SUPABASE_JWT_SECRET environment variable
```

Small fixes applied:

- `backend/rust/src/observability_auth.rs`: public demo mode now uses local auth defaults when Supabase auth env is intentionally absent.
- `Dockerfile.demo`: final chown now targets only writable runtime directories instead of recursively chowning `/app` and `/opt/venv`.

Rebuild after fixes:

- `docker build -f Dockerfile.demo -t omni-demo:validation .` passed.
- Rebuild duration: about 76 seconds.
- Image tag: `omni-demo:validation`

## Container Smoke Test Result

Container run:

```bash
docker run -d --name omni-demo-validation -p 3001:3001 omni-demo:validation
```

Startup:

```txt
API listening on http://0.0.0.0:3001 (host=0.0.0.0, port=3001, render_port_env=3001, observability_auth=enabled)
```

Health:

- `GET /health` returned `status=ok`
- Python entry exists and is observable.
- Node binary is observable.

Chat:

- `POST /chat` with `{"message":"ola","request_id":"smoke-001"}` returned a public-safe response.
- Response text: `Olá! Sou o Omni. Como posso te ajudar hoje?`
- Source: `python-subprocess`
- Runtime inspection was public-safe and contained no raw secrets, stack traces, stdout/stderr, or raw provider payload.

Invalid JSON:

- `POST /chat` with malformed JSON returned HTTP 400.
- Public code: `INVALID_JSON`
- `internal_error_redacted=true`

Oversized input:

- `POST /chat` with 8100 characters returned HTTP 413.
- Public code: `PAYLOAD_TOO_LARGE`
- `internal_error_redacted=true`

## Container Security Checks

Passed:

- `docker exec omni-demo-validation id`: `uid=999(omni) gid=999(omni)`
- Public demo env enabled in container.
- Shell tools disabled in env.
- Internal debug disabled in env.
- Rate limiting enabled in env.
- `OMNI_INTENT_CLASSIFIER=regex`
- `OMNI_MATCHER_MODE=enabled`
- `OMNI_PYTHON_MODE=subprocess`
- `OMNI_NODE_MODE=subprocess`
- `/var/run/docker.sock` absent inside container.
- `docker inspect` showed `Privileged=false`.
- `docker inspect` search found no `SUPABASE_JWT_SECRET`, provider keys, bearer token, or docker.sock.

Note:

- The smoke container was started with plain `docker run`, so compose-only hardening such as `cap_drop` and `read_only` is validated by compose config, not by the smoke container inspect.

## Rust Flake Evidence

Command:

```bash
cd backend/rust && cargo test
```

Result:

- 43 passed, 4 failed.
- Failed:
  - `run_control::tests::list_and_get_endpoints_return_structured_json`
  - `run_control::tests::pause_resume_approve_endpoints_return_ok`
  - `tests::call_python_merges_conversation_id_from_stdout_json`
  - `tests::call_python_returns_stderr_fallback`

Exact status mismatches:

- `run_control::tests::list_and_get_endpoints_return_structured_json`: left HTTP 500, right HTTP 200.
- `run_control::tests::pause_resume_approve_endpoints_return_ok`: left HTTP 500, right HTTP 200.
- `tests::call_python_merges_conversation_id_from_stdout_json`: expected `ok`, got degraded Rust/Python boundary response.
- `tests::call_python_returns_stderr_fallback`: expected `python_subprocess_nonzero_exit`, got `python_subprocess_timeout`.

Command:

```bash
cd backend/rust && cargo test -- --test-threads=1
```

Result:

- 45 passed, 2 failed.
- Failed:
  - `run_control::tests::list_and_get_endpoints_return_structured_json`
  - `run_control::tests::pause_resume_approve_endpoints_return_ok`

Command:

```bash
cd backend/rust && cargo test run_control -- --test-threads=1 --nocapture
```

Result:

- 1 passed, 2 failed.
- Deterministic status mismatch: HTTP 500 vs expected HTTP 200.

Manual CLI evidence:

- Direct Python CLI against a seeded registry returned `status=ok` for `list`.
- Direct Python CLI against the same seeded registry returned `status=ok` for `pause`.

Classification:

- `run_control` is no longer only a concurrency flake in this environment.
- It is a deterministic Rust test/harness or Rust-Axum-to-control-CLI integration failure.
- The underlying Python control CLI works manually with the same style of seeded registry.

Smallest follow-up:

- Add a focused follow-up phase to instrument `call_control_cli` test failures with public-safe response body capture, then fix the Rust test harness or integration path without broad runtime refactor.

## Validation Commands And Results

Passed:

- `docker --version`
- `docker compose version`
- `docker compose -f docker-compose.demo.yml config`
- `docker build -f Dockerfile.demo -t omni-demo:validation .`
- container `GET /health`
- container `POST /chat`
- container malformed JSON rejection
- container oversized input rejection
- container non-root/security/env checks
- `npm run validate:audit-pack`
- `npm run validate:public-demo`
- `npm run test:security`
- `npm test`
- `npm run test:js-runtime`
- `npm run test:python:pytest`
- `npm --prefix frontend run typecheck`
- `git diff --check`
- `cargo test observability_auth::tests::public_demo_mode_uses_local_auth_defaults_without_env_secret -- --exact --nocapture --test-threads=1`

Failed:

- `cd backend/rust && cargo test`
- `cd backend/rust && cargo test -- --test-threads=1`
- `cd backend/rust && cargo test run_control -- --test-threads=1 --nocapture`

## Remaining Blockers

- Superseded by `docs/audit/POST_ROADMAP_RUST_RUN_CONTROL_FIX.md`.
- Rust `run_control` tests now pass in focused, serial, and full Rust validation on branch `validation/rust-run-control-fix`.
- The remaining caveat is a local timeout while rebuilding a new Docker tag for the follow-up branch.

## Public Demo Decision

READY_FOR_CONTROLLED_DEMO: superseded by follow-up validation.

Reason:

- Docker build and public demo smoke were validated on this branch.
- Container security checks passed.
- Rust run_control evidence was later fixed/validated in `POST_ROADMAP_RUST_RUN_CONTROL_FIX.md`.

## Rollback

- Revert this validation branch commit.
- Remove the public-demo auth fallback if a different auth bootstrap strategy is chosen.
- Restore the previous Dockerfile final chown if needed, although that reintroduces very slow builds.
- Stop/remove local validation container:

```bash
docker rm -f omni-demo-validation
```

## No Merge Into Main

No merge into main, release tag, public deployment, or training run occurred.

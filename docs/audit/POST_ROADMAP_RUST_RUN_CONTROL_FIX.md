# POST-ROADMAP RUST RUN_CONTROL FIX

Branch: `validation/rust-run-control-fix`

Base branch: `validation/docker-demo-build-smoke`

Base commit: `5813bb28bbfdceaacfb64231356c8928a39db7c7`

Statement: focused Rust run_control investigation/fix and secret hygiene validation. No merge into main, no tag, no public deployment, no training run.

## Secret Hygiene Result

Passed:

- `.env` is ignored by `.gitignore`.
- `.env` is not tracked by git.
- `.env` was not staged.
- No `SUPABASE_JWT_SECRET` value was printed.
- No real secret was copied into Dockerfile, compose, docs, tests, snapshots, or logs.

Commands:

```bash
git status --short .env
git check-ignore -v .env
git ls-files .env
```

Observed:

```txt
.gitignore:2:.env .env
```

`git ls-files .env` returned no tracked file.

## Exact Failing Tests Before

Before the focused fix, Rust validation showed:

- `run_control::tests::list_and_get_endpoints_return_structured_json`: HTTP 500 vs expected HTTP 200.
- `run_control::tests::pause_resume_approve_endpoints_return_ok`: HTTP 500 vs expected HTTP 200.
- In parallel full runs, additional Python subprocess tests sometimes timed out, indicating environment/process contention.

Direct Python CLI evidence from the prior validation showed `list` and `pause` returned `status=ok` against the same style of seeded registry.

## Root Cause

Classification: Python control CLI startup/import occasionally exceeds the previous 5000ms Rust control boundary under Windows/Docker/Cargo load. This was not missing real Supabase secrets and not Python CLI failure.

Evidence:

- `.env` secrets are not required for tests.
- The run_control test harness uses dummy non-secret JWT material.
- Direct Python control CLI works manually.
- The failing Rust body was public-safe and explicit: `code=control_cli_timeout`, `control CLI timed out after 5000 ms`.
- After increasing the bounded control CLI timeout to 30 seconds, `run_control` passed in focused serial mode, full serial mode, and full Rust mode.
- Previous broad failures were reproducible under stressed/parallel Cargo/Docker conditions and then cleared after sequential execution.

## Fix Applied

Smallest safe fix:

- Added test-only `assert_status(...)` helper in `backend/rust/src/run_control.rs`.
- The helper reads and reports public-safe response bodies when a status assertion fails.
- Increased `CONTROL_TIMEOUT_MS` from 5000ms to 30000ms so Python control CLI startup/import latency does not fail valid control-route tests.
- Updated the run_control test harness timeout to match the bounded 30 second control timeout.
- Existing endpoint assertions remain strict: expected HTTP 200 is still required.
- No endpoint auth was bypassed.
- No runtime control route was made public.
- No real secrets were introduced.

Related existing validation fix preserved from the base branch:

- Public demo local auth fallback remains demo-only and requires `OMNI_PUBLIC_DEMO_MODE=true` or `OMINI_PUBLIC_DEMO_MODE=true`.
- Non-demo mode still requires real Supabase auth config.

## Auth And Demo Safety

- Protected run_control routes still require auth middleware.
- Tests use dummy non-secret JWT values.
- Public demo does not depend on real `SUPABASE_JWT_SECRET`.
- Non-demo mode does not use fake demo auth defaults.
- Error diagnostics added by this phase are test-only and do not expose raw env or secrets.

## Rust Run_Control Evidence

Passed:

```bash
cd backend/rust && RUST_BACKTRACE=1 cargo test run_control -- --test-threads=1 --nocapture
cd backend/rust && cargo test -- --test-threads=1
cd backend/rust && cargo test
```

Results:

- `run_control`: 3 passed, 0 failed.
- serial full Rust: 47 passed, 0 failed.
- full Rust: 47 passed, 0 failed.

## Docker Status

Passed:

```bash
docker compose -f docker-compose.demo.yml config
```

Previously passed on base validation:

- `docker build -f Dockerfile.demo -t omni-demo:validation .`
- container smoke `/health`
- container smoke `/chat`
- invalid JSON rejection
- oversized input rejection
- non-root/security/env checks

Attempted in this branch:

```bash
docker build -f Dockerfile.demo -t omni-demo:run-control-fix .
```

Result:

- Timed out after 30 minutes in local Docker Desktop.
- Existing image `omni-demo:validation` remains available.
- No Dockerfile regression was identified by compose config.

## Full Validation Results

Passed:

- `npm run validate:audit-pack`
- `npm run validate:public-demo`
- `npm run test:security`
- `npm test`
- `npm run test:js-runtime`
- `npm run test:python:pytest`
- `npm --prefix frontend run typecheck`
- `git diff --check`
- Rust commands listed above

Failed/blocked:

- `docker build -f Dockerfile.demo -t omni-demo:run-control-fix .` timed out locally.

## READY_FOR_CONTROLLED_DEMO

READY_FOR_CONTROLLED_DEMO: YES, with Docker caveat.

Reason:

- The Rust run_control blocker is now green.
- Security/public-demo/JS/Python/frontend validations passed.
- Docker compose config passed.
- Docker build and smoke already passed on the base validation image.
- The only remaining caveat is that the re-tagged Docker build for this branch timed out locally and should be rerun before sharing a demo URL.

## Rollback

Revert this branch commit to remove the test diagnostic helper and documentation. Do not remove `.env` ignore rules. Do not commit `.env`.

## No Merge Into Main

No merge into main, release tag, public deployment, or training run occurred.

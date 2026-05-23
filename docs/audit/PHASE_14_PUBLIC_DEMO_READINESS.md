# PHASE 14 PUBLIC DEMO READINESS

Branch: `release/public-demo-readiness-14`

Base branch: `intelligence/intent-classifier-12`

Base commit: `ba088e8da81253f9a6b04915610b0d648cdd67d7`

Statement: readiness validation and documentation only. No public deployment, release tag, training run, or merge into main.

## Files Changed

- `Dockerfile.demo`
- `docker-compose.demo.yml`
- `docs/audit/PHASE_14_PUBLIC_DEMO_READINESS.md`
- `docs/release/PUBLIC_DEMO_READINESS.md`
- `package.json`
- `scripts/validate_public_demo_readiness.mjs`

## Checks Performed

Security:

- Shell disabled in demo config.
- Public demo mode enabled through canonical and legacy env flags.
- Internal debug errors disabled.
- Security regression suite required and executed.
- No real-looking secrets allowed in demo docs/config by static validation.

Runtime truth:

- Matcher shortcuts documented as `MATCHER_SHORTCUT`.
- Fallback cannot be `FULL_COGNITIVE_RUNTIME`.
- Provider unavailable and tool blocked states documented.
- Classifier mode/source documented as safe public runtime truth fields.

API:

- Input validation, body/message limits, control-char handling, and rate limiting are covered by prior Rust tests and security suite.
- Invalid request non-invocation is covered by Phase 5 Rust tests.

Container:

- `Dockerfile.demo` exists.
- `docker-compose.demo.yml` exists.
- Non-root runtime user exists.
- Compose uses read-only filesystem, tmpfs writable paths, `cap_drop: ALL`, and `no-new-privileges`.
- Compose has no privileged mode and no Docker socket mount.
- `.dockerignore` excludes secrets, logs, build artifacts, storage, and caches.

Training safety:

- No training started.
- Training readiness remains dry-run/export-validation only.
- Unsafe records and low-truth events are excluded from positive candidates.

Persistent runtime:

- Subprocess mode remains the demo default.
- Service modes are opt-in.
- Circuit breaker/fallback behavior is documented.

## Required Demo Env

```txt
OMNI_PUBLIC_DEMO_MODE=true
OMINI_PUBLIC_DEMO_MODE=true
OMNI_ALLOW_SHELL_TOOLS=false
OMINI_ALLOW_SHELL_TOOLS=false
OMNI_DEBUG_INTERNAL_ERRORS=false
OMINI_DEBUG_INTERNAL_ERRORS=false
OMNI_RATE_LIMIT_ENABLED=true
OMNI_RATE_LIMIT_PER_MINUTE=30
OMNI_MAX_MESSAGE_CHARS=8000
OMNI_MAX_BODY_BYTES=65536
OMNI_INTENT_CLASSIFIER=regex
OMNI_MATCHER_MODE=enabled
OMNI_PYTHON_MODE=subprocess
OMNI_NODE_MODE=subprocess
```

Optional service-mode demo:

```txt
OMNI_PYTHON_MODE=service
OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS=true
```

## Validation Script

`scripts/validate_public_demo_readiness.mjs` checks:

- required files exist
- `test:security` and `validate:public-demo` scripts exist
- Dockerfile/compose set required public-demo env
- shell/debug are disabled
- rate limit is enabled
- regex/subprocess modes are default
- non-root/compose hardening settings exist
- `.dockerignore` covers secrets/logs/artifacts
- demo docs/config do not contain obvious real secret patterns

## Commands and Results

Passed:

- `npm run validate:public-demo`
- `npm run test:security`
- `npm test`
- `npm run test:js-runtime`
- `npm run test:python:pytest`
- `npm --prefix frontend run typecheck`
- `cd backend/rust && cargo test`
- `cd backend/rust && cargo test -- --test-threads=1`
- `python -m py_compile backend/python/brain_service.py backend/python/main.py`
- `docker compose -f docker-compose.demo.yml config`
- `git diff --check`

Transient issue observed:

- First `cargo test` attempt failed in two `run_control` tests with HTTP 500.
- Rerun with `--test-threads=1` passed 46 tests.
- Rerun of normal `cargo test` also passed 46 tests.
- No Rust/runtime code was changed in Phase 14.

## Docker Availability / Build Result

- `docker compose -f docker-compose.demo.yml config` passed.
- `docker build -f Dockerfile.demo -t omni-demo:phase14 .` was attempted.
- Docker build did not run because the local Docker daemon was unavailable:

```txt
ERROR: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: O sistema não pode encontrar o arquivo especificado.
```

## Known Limitations

- Static validation cannot prove runtime behavior by itself; it is paired with security, JS, Python, frontend, and Rust tests.
- Docker build depends on local Docker daemon availability.
- Demo rate limiting is process-local and should be backed by edge/platform controls for public traffic.
- This phase does not deploy, tag, or release.

## Rollback

Revert the Phase 14 commit and keep public demo disabled until readiness validation passes again.

## Gate 14

PASSED with Docker build limitation recorded:

- Public demo readiness doc exists.
- Public demo mode requirements are documented.
- Static validation verifies public-demo env, disabled shell/debug, rate limiting, Docker/compose hardening, `.dockerignore`, and obvious secret patterns.
- Security regression suite passed.
- Runtime/API/Rust/JS/Python/frontend validation passed.
- Docker compose config passed.
- Docker image build was blocked by unavailable local daemon and is recorded.
- Known limitations are documented.
- No deployment, release tag, training run, or merge into main occurred.

No merge into main.

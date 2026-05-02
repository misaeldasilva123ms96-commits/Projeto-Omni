# PHASE 6 — CONTAINERIZED PUBLIC DEMO MODE

Date: 2026-05-01

Base branch: security/input-rate-limit-05

Base commit: 8db77731547153ff294a239bad922ddc0a950f8d

Working branch: deploy/container-public-demo-06

## Scope

Phase 6 adds public-demo container configuration only. Runtime behavior, provider routing, CORS, cognitive execution, governance, shell policy, sanitizers, and rate limit semantics were not changed.

## Files Changed

- `Dockerfile.demo`
- `docker-compose.demo.yml`
- `.dockerignore`
- `docs/deploy/PUBLIC_DEMO_CONTAINER.md`
- `docs/audit/PHASE_6_CONTAINER_PUBLIC_DEMO.md`
- `tests/runtime/containerPublicDemo.validation.mjs`

## Container Safety Settings

- Multi-stage Rust build using `rust:1.88-bookworm`
- Verified Rust binary name from `backend/rust/Cargo.toml`: `omini-api`
- Runtime base: `node:20-bookworm-slim`
- Python virtualenv at `/opt/venv`
- `npm ci --omit=dev` with existing `package-lock.json`
- Runtime user: non-root `omni`
- API port: `3001`
- Health endpoint: `/health`
- No secrets baked into image

## Demo Env

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
```

## Runtime Dirs Copied

```txt
backend/python
backend/rust
core
configs
features
js-runner
observability
platform
runtime
storage
src
contract
```

## Compose Hardening

- no privileged mode
- no Docker socket mount
- `cap_drop: ["ALL"]`
- `security_opt: ["no-new-privileges:true"]`
- `read_only: true`
- tmpfs for `/tmp`, `.logs`, Python memory/transcripts/sessions, and `storage/local`
- no raw secrets
- healthcheck uses confirmed `/health` endpoint

## Dockerignore Coverage

The `.dockerignore` now excludes git metadata, env files, node modules, Rust targets, build outputs, logs, runtime logs, learning logs, local storage, trace/debug JSON, Python caches, and pytest cache while preserving `.env.example`.

## Validation Commands / Results

- `node tests/runtime/containerPublicDemo.validation.mjs`: passed
- `docker compose -f docker-compose.demo.yml config`: passed
- `npm test`: passed
- `npm run test:js-runtime`: passed
- `npm run test:python:pytest`: passed
- `cd backend/rust && cargo test`: one known flaky concurrent `run_control::tests::list_and_get_endpoints_return_structured_json` failure reproduced
- `cd backend/rust && cargo test -- --test-threads=1`: passed, 38 tests
- `git diff --check`: passed
- `docker build -f Dockerfile.demo -t omni-demo:phase6 .`: not executed successfully because Docker daemon was unavailable in the local environment

Docker availability result:

```txt
Docker version 29.3.1
Docker Compose version v5.1.1
docker build failed to connect to npipe:////./pipe/dockerDesktopLinuxEngine
```

## Known Limitations

- In-memory rate limiting is per process; use edge/platform rate limiting for public traffic.
- Demo writable paths are ephemeral tmpfs paths.
- This profile intentionally does not include provider secrets.

## Rollback

Revert the Phase 6 commit on `deploy/container-public-demo-06`.

## Gate 6 Status

Status: PASSED with Docker daemon unavailable for image build. Static container validation, compose config, repo tests, serial Rust test suite, and diff checks passed.

## No Merge Into Main

This phase does not merge into main.

# Public Demo Readiness

Status: ready for controlled validation, not public deployment.

Branch: `release/public-demo-readiness-14`

Base: `intelligence/intent-classifier-12`

This document is the public-demo readiness checklist for Omni. It does not authorize a release, deployment, tag, or production launch.

## Required Demo Environment

Use these defaults for a controlled public demo:

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

Optional internal service-mode demo only:

```txt
OMNI_PYTHON_MODE=service
OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS=true
```

Do not expose Python or Node internal services publicly.

## Safe Run Instructions

Static readiness validation:

```bash
npm run validate:public-demo
```

Security regression suite:

```bash
npm run test:security
```

Container validation:

```bash
docker compose -f docker-compose.demo.yml config
docker build -f Dockerfile.demo -t omni-demo:phase14 .
```

Run locally:

```bash
docker compose -f docker-compose.demo.yml up --build
```

Health endpoint:

```txt
http://localhost:3001/health
```

Chat endpoint:

```txt
http://localhost:3001/chat
```

## Security Guarantees

- Shell tools are disabled by public-demo config.
- Public demo mode wins over shell allow flags.
- Dangerous shell/tool patterns remain blocked by Phase 1A and Phase 3 controls.
- Sensitive tools are governed before execution.
- Internal debug errors are disabled.
- Public backend payloads are sanitized before frontend/API exposure.
- Frontend runtime debug payloads are sanitized defensively.
- Specialist/runtime errors use public-safe taxonomy and redaction.
- Learning/runtime logs redact PII, secrets, paths, and internal payloads before persistence.
- Provider and Supabase diagnostics expose booleans/status only, not raw keys or env.
- `.env.example` uses placeholders only.

## Runtime Truth Checklist

- Matcher shortcuts are labeled `MATCHER_SHORTCUT`.
- Fallback paths are never labeled `FULL_COGNITIVE_RUNTIME`.
- Provider unavailable states are labeled with public-safe error taxonomy.
- Blocked tools are labeled `TOOL_BLOCKED`.
- Classifier mode/source are visible through safe runtime truth fields.
- Regex intent classification remains the default.

## API Checklist

- `/chat` validates `Content-Type`.
- Invalid JSON is rejected before runtime invocation.
- Empty, oversized, and unsafe-control-character messages are rejected.
- Message/body limits are active.
- Rate limiting is enabled by default in demo config.
- Invalid requests do not invoke Python/Node runtime.

## Container Checklist

- `Dockerfile.demo` exists.
- `docker-compose.demo.yml` exists.
- Runtime runs as non-root user `omni`.
- Compose uses `read_only: true`.
- Compose drops Linux capabilities.
- Compose sets `no-new-privileges`.
- Compose does not use privileged mode.
- Compose does not mount `docker.sock`.
- Docker/compose files do not contain provider keys or Supabase service secrets.
- `.dockerignore` excludes secrets, logs, local storage, build output, and caches.

## Training Safety Checklist

- No training is started.
- Training export remains dry-run by default.
- Unsafe records are excluded.
- Fallback, matcher shortcut, tool-blocked, provider-failure, and governance-block cases are not positive examples.
- Eval seed data is synthetic and safe.

## Persistent Runtime Checklist

- Subprocess mode remains the public-demo default.
- Python service mode is opt-in.
- Circuit breaker/fallback behavior is documented.
- Service mode failures use public-safe taxonomy and cannot claim full runtime success.

## Test Evidence Summary

Required Phase 14 validation commands:

- `npm run validate:public-demo`
- `npm run test:security`
- `npm test`
- `npm run test:js-runtime`
- `npm run test:python:pytest`
- `npm --prefix frontend run typecheck`
- `cd backend/rust && cargo test`
- `python -m py_compile backend/python/brain_service.py backend/python/main.py`
- `git diff --check`

Docker status is recorded in `docs/audit/PHASE_14_PUBLIC_DEMO_READINESS.md`.

## Manual Checklist Before Public Demo

- Confirm no real provider keys are configured in public-demo environment.
- Confirm no Supabase service role key is available to the demo container.
- Confirm platform-level rate limiting or edge protection for real public traffic.
- Confirm logs are ephemeral or stored in a protected location.
- Confirm no internal Python/Node service ports are exposed.
- Confirm browser UI debug panels show public-safe fields only.
- Confirm rollback path is available before sharing any demo URL.

## Not Production

This profile is for a controlled public demo only. It is not a production deployment profile. Multi-instance rate limiting, provider quota management, WAF/edge policies, audit retention, and operational monitoring must be configured separately.

## Known Limitations

- Rate limiting is in-memory and per process.
- Demo writable state is ephemeral in compose tmpfs paths.
- Intent classifier is regex by default; embedding/LLM modes are not production classifiers.
- Node and Python service modes are opt-in and not the public-demo default.
- Docker build success depends on local Docker daemon availability.

## Rollback

- Revert the Phase 14 commit.
- Remove `validate:public-demo` script usage.
- Restore previous `Dockerfile.demo` and `docker-compose.demo.yml` env blocks if needed.
- Keep public demo disabled until readiness checks pass again.

## No Merge Into Main

No merge into `main`, release tag, or public deployment is part of this phase.

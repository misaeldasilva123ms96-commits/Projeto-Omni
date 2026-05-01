# Public Demo Container

This container profile runs the Rust API with the Python brain and Node QueryEngine in one public-demo image. It is intended for safe debugging/demo exposure, not for unrestricted production traffic.

## Build

```bash
docker build -f Dockerfile.demo -t omni-demo:phase6 .
```

## Run

```bash
docker run --rm -p 3001:3001 omni-demo:phase6
```

The API is exposed on:

```txt
http://localhost:3001/health
http://localhost:3001/chat
```

## Compose

```bash
docker compose -f docker-compose.demo.yml up --build
```

Validate the compose file:

```bash
docker compose -f docker-compose.demo.yml config
```

## Demo Environment

The demo image and compose file set:

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

`OMNI_*` is the canonical prefix. `OMINI_*` is kept for legacy compatibility where the runtime already supports it.

## Forbidden Secrets

Do not pass provider keys, Supabase service role keys, tokens, raw env dumps, private memory stores, local databases, or real user logs into this demo profile.

If a provider key is needed for a private environment, use the normal deployment path and platform secret manager instead of baking it into a Dockerfile or compose file.

## Security Posture

The demo profile:

- runs as non-root user `omni`
- enables public demo mode
- disables shell tools
- disables internal debug error detail
- enables Rust API input limits and rate limiting
- uses a read-only root filesystem in compose
- uses tmpfs for writable runtime scratch paths
- drops Linux capabilities in compose
- sets `no-new-privileges`
- does not mount Docker socket
- does not use privileged mode

## Runtime Directories

The demo Dockerfile copies the runtime directories required by the current Rust/Python/Node path:

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

## Rate Limit Note

The Rust rate limiter is in-memory and per process. Use an edge, reverse proxy, or platform-level rate limiter for real public traffic and multi-instance deployments.

## Known Limitations

- Container-local writable data is ephemeral in demo compose tmpfs paths.
- The profile is not a substitute for provider-specific production secret handling.
- Multi-instance global rate limiting is out of scope for this phase.

## Rollback

Remove `Dockerfile.demo`, `docker-compose.demo.yml`, the Phase 6 docs, and the `.dockerignore` additions, or revert the Phase 6 commit.

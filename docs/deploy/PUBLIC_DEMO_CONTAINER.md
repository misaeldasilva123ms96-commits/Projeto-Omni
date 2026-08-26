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
http://localhost:3001/api/v1/runtime/runner-smoke
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
OMNI_ALLOW_SHELL_TOOLS=false
OMNI_DEBUG_INTERNAL_ERRORS=false
OMNI_RATE_LIMIT_ENABLED=true
OMNI_RATE_LIMIT_PER_MINUTE=30
OMNI_RATE_LIMIT_MAX_CLIENTS=10000
OMNI_TRUST_PROXY_HEADERS=false
OMNI_TRUSTED_PROXY_CIDRS=
OMNI_TRUST_PROXY_MAX_HOPS=8
OMNI_MAX_MESSAGE_CHARS=8000
OMNI_MAX_BODY_BYTES=65536
BASE_DIR=/app
OMNI_BASE_DIR=/app
NODE_RUNNER_BASE_DIR=/app
```

`OMNI_*` is the exclusive runtime configuration prefix.

`/app` is the canonical Node runner root. The profile does not configure
`RUNNER_SCHEMA_PATH`, `RUNNER_ADAPTER_PATH`, `NODE_OPTIONS`, or `NODE_PATH`.
The runner, schema, adapters, engine candidates, cwd, and agent-memory roots
must satisfy the shared path policy before use; public diagnostics retain only
safe labels such as `app` or repository-relative artifact labels.

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

## Runtime Smoke Diagnostic

`GET /api/v1/runtime/runner-smoke` is a public-safe production diagnostic for deployment mismatches. It executes the same Node runner path used by chat with a fixed safe prompt and returns only bounded metadata:

- selected runtime (`node`, `bun`, or `unknown`)
- cwd label (`app`, `repo`, or `unknown`)
- runner/adapter/fusion/contract existence booleans
- runner exit code
- stdout JSON validity
- degraded boolean
- public failure class and summary

It must not expose raw stdout/stderr, env values, stack traces, headers, provider payloads, request bodies, API keys, or absolute local paths. The diagnostic subprocess scrubs provider credential/url envs so it does not make real provider calls.

## Rate Limit Note

The Rust rate limiter uses the actual TCP peer IP by default, stores at most
`OMNI_RATE_LIMIT_MAX_CLIENTS` active process-local buckets, and keeps the
existing 60-second sliding window. `Forwarded` and `X-Real-IP` are intentionally
ignored. `X-Forwarded-For` is also ignored while
`OMNI_TRUST_PROXY_HEADERS=false`.

Operators may enable `X-Forwarded-For` only when they configure
`OMNI_TRUSTED_PROXY_CIDRS` with the exact immediate reverse-proxy IPs or CIDR
networks for their deployment. The repository does not guess ranges for
Cloudflare, Render, Netlify, Kubernetes, Docker, or another platform. Plain IP
addresses are exact (`/32` for IPv4 and `/128` for IPv6), blanket `/0` networks
are rejected, and invalid configuration stops startup. A trusted chain is
bounded to 8 hops and 8192 total header bytes by default, is parsed strictly,
and is resolved from right to left. Malformed or unresolvable chains fall back
to the actual peer without exposing or logging the raw header.

The limiter is in-memory and per process. Use an edge, reverse proxy, or
platform-level limiter for real public traffic and multi-instance deployments.

The client-identity and bounded-map behavior was validated at technical commit
`f70d209998e315b1e63dd8ceffdf1560c8a8c2aa`, including the successful
[Docker Runtime Smoke run 30752270121](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270121).
See the
[commit-bound hardening evidence](../audit/2026-08-02-trusted-proxy-rate-limit-hardening.md)
for the exact tests, dependency scans, workflow runs, and retained limitations.

## Known Limitations

- Container-local writable data is ephemeral in demo compose tmpfs paths.
- The profile is not a substitute for provider-specific production secret handling.
- Multi-instance global rate limiting is out of scope for this phase.
- Node path validation is application-level and is not an operating-system
  sandbox. It does not eliminate privileged local replacement or filesystem
  TOCTOU risk, and it adds no seccomp, AppArmor, or SELinux policy.

The Node runner containment was validated at authoritative technical head
`a6f6b34e79f560e9dfc71455d1ef63ab893c96f7`, including built-in bootstrap
validation of `js-runner/pathPolicy.js`, pre-import validation of
`core/brain/fusionBrain.js`, and successful
[Docker Runtime Smoke run 30760386640](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30760386640).
See the
[commit-bound containment evidence](../audit/2026-08-02-node-runner-path-containment.md)
for the exact policy, tests, workflow runs, and retained limitations.

## Rollback

Remove `Dockerfile.demo`, `docker-compose.demo.yml`, the Phase 6 docs, and the `.dockerignore` additions, or revert the Phase 6 commit.

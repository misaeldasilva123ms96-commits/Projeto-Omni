# Trusted Proxy and Rate-Limit Hardening Evidence

**Evidence date:** 2026-08-02

**Source `main`:** `f23f2b28f0e770b256d34c30e05963566b23484e`

**Branch:** `hardening/trusted-proxy-rate-limit`

**Technical commit:** `f70d209998e315b1e63dd8ceffdf1560c8a8c2aa`

**Pull request:** [#603](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/603) (draft)

This report records commit-bound preparation and validation evidence. It does
not claim production readiness, authorize deployment, or replace manual review
and merge ownership.

## Prior behavior and threat model

Before the technical commit, the Rust API did not attach Axum connection
metadata to chat requests. With proxy trust disabled, unrelated clients shared
one `global` rate-limit key. With proxy trust enabled, the first
comma-separated `X-Forwarded-For` value could become the key without proving
that the TCP peer was an authorized proxy. The map used arbitrary strings,
allowed no operator-defined bucket ceiling, and evicted a bucket when full.

The attacker-controlled input is forwarding metadata on a public chat request.
The protected boundary is the client identity used by the process-local
limiter. A header must never select an identity unless the immediate TCP peer
belongs to an explicitly configured trusted proxy network.

## Peer-address integration and secure default

The server now uses
`app.into_make_service_with_connect_info::<SocketAddr>()`. Both `/chat` and
`/api/v1/chat` extract the resulting connection metadata through one shared
validation path. Tests inject `ConnectInfo<SocketAddr>` explicitly.

`OMNI_TRUST_PROXY_HEADERS=false` remains the default. In that mode,
`X-Forwarded-For`, `Forwarded`, and `X-Real-IP` are ignored and the normalized
TCP peer `IpAddr` is the key. Different peers have independent buckets; one
peer cannot create buckets by changing spoofed headers. Missing peer metadata
returns a redacted `INTERNAL_ERROR_REDACTED` server response before Python,
Node, providers, tools, or cognitive runtime can run.

## Configuration contract

The configuration is parsed once during startup:

```text
OMNI_TRUST_PROXY_HEADERS=false
OMNI_TRUSTED_PROXY_CIDRS=
OMNI_TRUST_PROXY_MAX_HOPS=8
OMNI_RATE_LIMIT_MAX_CLIENTS=10000
```

`OMNI_TRUSTED_PROXY_CIDRS` accepts comma-separated IP addresses or CIDR
networks. Plain IPv4 and IPv6 addresses are exact `/32` and `/128` networks.
Trust enabled with an empty set, invalid or empty entries, and blanket
`0.0.0.0/0` or `::/0` networks fail startup with sanitized errors. Hop counts
must be 1 through 64. Client capacity must be 1 through 1,000,000. The
canonical `OMNI_*` prefix remains exclusive; no obsolete alias was added.

Tests used only documentation networks and loopback identities, including
`10.0.0.0/8`, `192.0.2.0/24`, `2001:db8::/32`, `10.0.0.1`, `127.0.0.1`, and
`::1`. The repository demo config contains no generic trusted proxy range.

## Trusted-chain algorithm

Only `X-Forwarded-For` is eligible in this cycle. `Forwarded` and
`X-Real-IP` are intentionally ignored.

For an immediate peer in the configured trusted networks, the resolver reads
all `X-Forwarded-For` field instances in wire order, accounts for at most 8192
total raw bytes, splits comma-separated elements, trims optional whitespace,
strictly parses every element as `std::net::IpAddr`, normalizes IPv4-mapped
IPv6 addresses to IPv4, and enforces the configured hop ceiling. It then walks
from right to left, skips configured trusted proxy addresses, and chooses the
first untrusted address.

An untrusted immediate peer bypasses header parsing and always uses its TCP
peer IP. A missing, empty, non-UTF-8, malformed, over-byte, over-hop, quoted,
port-suffixed, or otherwise invalid chain falls back deterministically to the
actual peer. An all-trusted chain also falls back to the peer. Logs use only a
generic classification and never include raw header values or effective IPs.

## Bounded limiter behavior

The 60-second process-local sliding window is unchanged. Keys are normalized
`IpAddr` values. Expiration cleanup, capacity decision, bucket lookup or
creation, admission, and timestamp insertion remain atomic under one limiter
lock. The lock is released before parsing JSON, running subprocesses, calling
providers, logging, networking, or generating a response.

At `OMNI_RATE_LIMIT_MAX_CLIENTS` capacity, expired or empty buckets are pruned.
If the active map remains full, a new identity receives the existing redacted
`RATE_LIMITED` response. No active client is evicted and no overflow map is
created. Existing clients continue through their current buckets. With the
limiter disabled, identity still fails safely when peer metadata is missing,
but successful requests do not populate the bucket map.

## Focused and regression validation

Fresh local results on the technical commit's content:

- `git diff --check`: passed.
- `cargo fmt --manifest-path backend/rust/Cargo.toml -- --check`: passed.
- `cargo test --manifest-path backend/rust/Cargo.toml --locked --all`: 170
  passed, 0 failed.
- `cargo clippy --manifest-path backend/rust/Cargo.toml --locked --all-targets
  --all-features -- -D warnings`: passed.
- `npm run validate:public-demo`: passed.
- `npm run validate:audit-pack`: passed.
- `npm run validate:env-aliases`: passed with 0 active obsolete references.
- `npm run test:security`: passed with the repository security venv. The first
  invocation selected a Hermes Python lacking `pytest` and stopped before the
  suite; the same command then passed after placing the prepared Python 3.11
  security venv first on `PATH`.
- `node --test tests/runtime/containerPublicDemo.validation.mjs`: passed.
- `bash scripts/docker-runtime-smoke.sh` through Git for Windows Bash: passed.

The 170 Rust tests include direct peer independence, same-peer spoof
resistance, trusted right-to-left chains, leftmost spoof rejection, untrusted
immediate peers, all-trusted fallback, duplicate header fields, malformed and
bounded inputs, IPv4/IPv6/mapped normalization, startup configuration, expired
bucket pruning, full active-map rejection, existing-client continuity,
disabled-map behavior, same-client atomic concurrency, distinct-client
isolation, both chat routes, missing-peer failure, and runtime non-invocation
for identity and capacity blocks. Existing body, message, JSON, content-type,
ID, and Runtime Truth regressions also passed.

The local daemon-backed smoke used Docker Engine 29.4.1 and Compose 5.1.3,
built image
`sha256:dcb1e4e3f3766f8e91fd20dea3b76897d34c210a4812c5a534e280d329499a86`,
verified the controlled-demo routes and hardening, reported
`DIRECT_LOCAL_RESPONSE_WITH_PROVIDER_UNAVAILABLE`, and completed SIGTERM
shutdown with exit 0.

## Dependency and secret validation

The focused direct dependency `ipnet = "2"` was added. `ipnet 2.12.0` already
existed transitively in `Cargo.lock`; the lock change only records it as a
direct dependency of `omni-api`.

- Root `npm audit --audit-level=high`: 0 vulnerabilities.
- Frontend `npm audit --audit-level=high`: 0 vulnerabilities.
- `pip-audit -r backend/python/requirements.txt`: no known vulnerabilities.
- `(cd backend/rust && cargo audit)`: no blocking advisories; the existing
  allowed yanked warning for `spin 0.9.8` remains.
- Gitleaks 8.30.1 scanned each changed technical file and
  `origin/main..f70d209998e315b1e63dd8ceffdf1560c8a8c2aa`: no leaks found.

## Authoritative implementation-head workflows

GitHub marks the technical commit signature as verified (`reason: valid`). All
workflow runs associated with that exact head completed successfully:

| Workflow | Run | Conclusion |
| --- | --- | --- |
| Omni Public Demo CI | [30752270086](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270086) | success |
| CI | [30752270087](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270087) | success |
| Pull Request Labeler | [30752270090](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270090) | success |
| Omni Rust CI | [30752270103](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270103) | success |
| Omni Python CI | [30752270108](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270108) | success |
| Frontend CI | [30752270111](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270111) | success |
| Omni Security CI | [30752270112](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270112) | success |
| Issue & PR Automation | [30752270117](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270117) | success |
| Omni Live E2E CI | [30752270118](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270118) | success |
| Docker Runtime Smoke | [30752270121](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270121) | success |
| Omni Runtime CI | [30752270123](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270123) | success |
| Security Checks | [30752270138](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270138) | success |
| Lint & Static Checks | [30752270160](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270160) | success |
| Omni Node CI | [30752270246](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270246) | success |

The authoritative Docker job is
[91508286062](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30752270121/job/91508286062).
It used Docker 28.0.4 and Compose 2.38.2, built image
`sha256:8e812c9b1593948bf8eb2f3d07c07ac3d871f91271547552245f8286051e1b22`,
reported `DIRECT_LOCAL_RESPONSE_WITH_PROVIDER_UNAVAILABLE`, and completed
SIGTERM shutdown with exit 0.

## Residual limitations

- The limiter is process-local.
- Limiter state resets on process restart.
- Multiple replicas require edge or platform enforcement.
- Trusted proxy configuration is deployment-specific.
- No WAF validation was performed.
- No hostile internet traffic test was performed.
- No production deployment validation was performed.
- No multi-instance coordination was implemented or validated.
- No distributed rate-limit store was implemented.
- No penetration test was performed.

This pull request must not be merged automatically. Final review and merge
remain manual and exclusive to Misael.

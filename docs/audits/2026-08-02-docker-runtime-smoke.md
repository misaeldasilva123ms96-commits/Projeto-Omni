# Controlled-demo Docker runtime smoke evidence — 2026-08-02

## Evidence identity

- Source `main`: `5cd52e02d7d18cc3ae809b77a8289c3144e4b42f`
- Branch: `hardening/docker-runtime-smoke`
- Implementation commits:
  - `2ba3aa387d124f20363214c2bf90db24c7f18577` — runtime smoke, focused packaging/runtime corrections, tests, and workflow
  - `9e6d3df8c2affc08865c7d0b588e3ad42f0880e3` — final implementation head and non-sensitive toolchain evidence
- Draft pull request: [#602](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/602)
- GitHub Actions run: [30729056467](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30729056467)
- Job: [Controlled-demo runtime smoke 91445928032](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30729056467/job/91445928032)
- Run conclusion: `success`
- Tested head SHA: `9e6d3df8c2affc08865c7d0b588e3ad42f0880e3`

## Tested environment and image

- GitHub-hosted runner Docker server: `28.0.4`
- Docker Compose: `2.38.2`
- Built image ID: `sha256:c017073e46aa0660144ce213bde190ec1b3234d4080bfcadb1b0683e641ff238`
- Canonical entry point: `bash scripts/docker-runtime-smoke.sh`
- Compose project: unique per run (`omni-smoke-30729056467-1-2422` in the recorded run)
- Container process user: `omni` (non-root; local daemon-backed verification resolved UID `999`)
- No provider credential or billable provider request was used. The gate generated synthetic per-run auth material only to satisfy the existing fail-closed observability configuration and a separate synthetic sentinel for leak detection.

The same implementation also passed locally with Docker Engine `29.4.1`, Docker Compose `v5.1.3`, image `sha256:4551613e4af18150e01c689ef6fc756f4633d95ea2dd029d281777284abe4e18`, and shutdown exit `0`. Image IDs differ across builder environments and are recorded separately rather than treated as portable release identifiers.

## Effective hardening assertions

The running container satisfied all of the following assertions:

- non-root `omni` process user;
- read-only root filesystem;
- `cap_drop: ALL` effective;
- `no-new-privileges:true` effective;
- expected tmpfs mounts at `/tmp`, `/app/.logs`, `/app/backend/python/memory`, `/app/backend/python/transcripts`, `/app/backend/python/brain/runtime/sessions`, and `/app/storage/local`;
- container port `3001/tcp` published only through the run-selected host port;
- protected write under `/app` failed with `Read-only file system`;
- write and cleanup under approved `/tmp` succeeded;
- restart count remained zero.

No privileged mode, Docker socket, broad writable bind mount, or relaxed container control was added.

## Endpoint and positive checks

The gate built `Dockerfile.demo` through `docker-compose.demo.yml`, started the real Compose service, waited at most 120 seconds, and required `running|healthy|0` before requests.

| Endpoint | Result | Assertions |
| --- | --- | --- |
| `GET /health` | HTTP 200 | Valid canonical JSON; `status=ok`; `rust_service=ok`; positive runtime session version; truthful Python and Node dependency states; no synthetic material |
| `GET /api/v1/status` | HTTP 200 | API version 1; status/runtime/Rust/Python/Node/session fields; no operator-only `configured_bin` or `entry`; no host path, stack trace, credential, or sentinel |
| `POST /chat` | HTTP 200 | Non-empty response, session and source; runtime session version; supplied `client_session_id` preserved; Runtime Truth evaluated |
| `POST /api/v1/chat` | HTTP 200 | Same execution contract plus API version 1; correlation preserved; Runtime Truth evaluated |

Transport success alone was not accepted as cognitive success.

## Runtime Truth result

The deterministic harmless prompt `Olá!` produced:

- outer `runtime_mode=DIRECT_LOCAL_RESPONSE`;
- nested `runtime_truth.runtime_mode=PROVIDER_UNAVAILABLE`;
- `provider_actual=local-heuristic`;
- no LLM provider attempt or success;
- no tool invocation or execution;
- no `FULL_COGNITIVE_RUNTIME` claim.

This is a truthful local response with explicit provider-unavailable degradation evidence. It is not provider-backed cognitive execution and is not recorded as such.

## Negative and containment checks

- Malformed JSON returned HTTP `400` with `error_public_code=INVALID_JSON`, a public message, and `internal_error_redacted=true`.
- An `8001`-character message exceeded the unchanged public-demo limit and returned HTTP `413` with `error_public_code=PAYLOAD_TOO_LARGE`, a public message, and `internal_error_redacted=true`.
- After both negative requests, the container remained running and healthy with restart count zero.
- The protected-root and approved-tmpfs write checks both behaved as required.

## Leakage and diagnostic result

The unique synthetic sentinel and synthetic auth material were checked against health, status, both chat responses, both negative responses, container logs, and sanitized diagnostics. No exact synthetic value was found. Public response validation also rejected Rust panic markers, Python traceback, Node stack shapes, GitHub runner paths, Windows host paths, authorization bearer values, and credential-like values.

Container logs contained no sentinel, panic, unhandled exception, fatal traceback, credential value, or authorization token. Failure diagnostics exclude the Docker environment array, redact synthetic/auth/path material, are scanned after sanitization, and are uploaded only on failure. The successful recorded job therefore skipped the artifact-upload step.

Gitleaks `v8.28.0` found no leaks in the implementation commit, the branch diff, or task commits. The GitHub `Secret Scan (Gitleaks)` check also passed.

## Shutdown and cleanup

The gate stopped the service through `docker stop --time 20`, which sends the normal SIGTERM path. The application exited with code `0`, was not OOM-killed, did not restart, and did not require SIGKILL. Exit `137` is an explicit gate failure. Compose containers, networks, volumes, the unique image tag, override file, and temporary raw resources were removed by the registered cleanup path.

## Discovery failures encountered and corrected

1. **Test-harness deficiency:** the first exploratory run cleaned up before retaining crash diagnostics. Diagnostic collection was moved into the registered failure cleanup.
2. **Compose configuration problem:** the unmodified service failed closed because required Supabase observability auth was absent. The gate now injects random test-only auth material and a non-production issuer without logging or publishing it; runtime auth was not weakened.
3. **Docker/runtime packaging defect:** Python initialization attempted to write evolution and swarm state inside the read-only application tree. Public demo now disables its background evolution loop and routes required ephemeral state to the existing approved `/app/storage/local` tmpfs.
4. **Runtime public-safety defect:** subprocess stderr/traceback detail could reach the public fallback envelope and logs. Public-demo fallback detail and health detail are now redacted, with a focused Rust regression test.
5. **Runtime lifecycle defect:** the baseline container did not exit within `docker stop --time 20` and was killed with exit `137`. Axum now drains through a SIGTERM-aware graceful-shutdown future; the recorded run exited `0`.
6. **Incorrect expectations:** the canonical health value is `rust_service="ok"`, and the observed stable no-provider path is `DIRECT_LOCAL_RESPONSE` with nested `PROVIDER_UNAVAILABLE`, not an assumed matcher classification. Validator fixtures now encode the observed canonical contract.

## Additional validation

- `npm ci` and `npm ci --prefix frontend`: passed; the Windows host Node `24.14.1` emitted the repository engine warning requiring `>=24.15`, while the tested demo image uses Node `24.15`.
- `npm run validate:public-demo`, `validate:audit-pack`, and `validate:env-aliases`: passed.
- `npm run test:security`: passed in an isolated pytest environment.
- Node runtime/static smoke validators: 4 passed.
- Focused Python writable-path tests: 2 passed.
- Python prompt Runtime Truth table: 5 passed.
- `cargo fmt -- --check`: passed.
- `cargo test --locked --all`: 145 passed.
- `cargo clippy --locked --all-targets --all-features -- -D warnings`: passed.
- `git diff --check`: passed.

## Checks not performed and residual limitations

No real provider call, provider credential, billable request, target-platform deployment, production profile, hostile-traffic exercise, multi-instance test, penetration test, target-platform secret injection/rotation, WAF validation, regional failover test, or production monitoring/incident-response validation was performed. The rate limiter, circuit breaker, and relevant runtime state remain process-local. The demo Compose profile remains a controlled-demo profile, not a production deployment profile.

A successful GitHub-hosted runner smoke test proves that the controlled-demo
image built and executed under the tested CI environment. It does not prove
production readiness, hostile-traffic resistance, multi-instance behavior,
target-platform secret management, or target-platform deployment health.

Final review and merge remain manual and exclusive to the repository owner. The pull request remains draft; no merge or auto-merge was performed.

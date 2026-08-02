# Controlled-demo Docker runtime smoke evidence — 2026-08-02

## Evidence identity

- Source `main`: `5cd52e02d7d18cc3ae809b77a8289c3144e4b42f`
- Branch: `hardening/docker-runtime-smoke`
- Implementation commits:
  - `2ba3aa387d124f20363214c2bf90db24c7f18577` — runtime smoke, focused packaging/runtime corrections, tests, and workflow
  - `9e6d3df8c2affc08865c7d0b588e3ad42f0880e3` — initial implementation head and non-sensitive toolchain evidence
  - `d9a0be591c52645aa3bf08f03b9f72a6340f1340` — fail-closed diagnostic publication, cleanup integrity, and `.dockerignore` trigger correction
- Technical correction signature: valid GitHub-verified GPG signature (`reason=valid`)
- Draft pull request: [#602](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/pull/602)
- Authoritative GitHub Actions run: [30731215303](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30731215303)
- Authoritative job: [Controlled-demo runtime smoke 91451875585](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30731215303/job/91451875585)
- Run conclusion: `success`
- Tested head SHA: `d9a0be591c52645aa3bf08f03b9f72a6340f1340`

The authoritative runtime evidence is bound to the technical implementation
commit and its successful Docker Runtime Smoke run. The documentation commit
does not attempt to reference its own immutable SHA.

The earlier successful [run 30729056467](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30729056467)
remains historical implementation evidence. It is superseded as authoritative
evidence because its diagnostic publication and final cleanup paths were not
yet strictly fail-closed.

## Tested environment and image

- GitHub-hosted runner Docker server: `28.0.4`
- Docker Compose: `2.38.2`
- Built image ID: `sha256:f0de92d5eaf6f41df0f5da6647ffdcbf581d2f99a61e221b726a41b0c81e32e2`
- Canonical entry point: `bash scripts/docker-runtime-smoke.sh`
- Compose project: unique per run (`omni-smoke-30731215303-1-2248` in the authoritative run)
- Container process user: `omni` (non-root; local daemon-backed verification resolved UID `999`)
- No provider credential or billable provider request was used. The gate generated synthetic per-run auth material only to satisfy the existing fail-closed observability configuration and a separate synthetic sentinel for leak detection.

The corrected implementation also passed locally with Docker Engine `29.4.1`,
Docker Compose `v5.1.3`, image
`sha256:68587da0e70b633ef74b323ba7e8a6fa8cad85ee375ce72fd43b019bfdcde311`,
and shutdown exit `0`. Independent post-run checks found no project
containers, networks, volumes, or temporary image tag. Image IDs differ across
builder environments and are recorded separately rather than treated as
portable release identifiers.

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

Container logs contained no sentinel, panic, unhandled exception, fatal
traceback, credential value, or authorization token. Failure diagnostics do not
include the Docker environment array or raw logs in the publication directory.
Every selected raw file is transformed into a distinct `-sanitized` regular
file in a private staging directory. The complete staging directory is scanned
before the non-sensitive `.safe-to-upload` marker is created. Publication is
then re-verified for exact marker content, regular sanitized files, absence of
raw filenames, symlink/junction rejection, and the canonical full-directory
content rules. GitHub independently reruns this verifier and uploads only when
it emits `safe_to_upload=true`. A failed sanitizer, scan, marker check, or
workflow re-verification removes or withholds the publication directory and
prints only a generic safety message. The authoritative successful job skipped
both failure-only verification and artifact upload.

The focused Node suite passed 8/8 tests on Windows and in the authoritative
Ubuntu job. It proved a safe fixture is authorized; an unsafe fixture containing
traceback, panic, sentinel, bearer material, and host paths is rejected with no
marker or publication directory; injected sanitizer failure is withheld; raw
filenames and symlink/junction escapes are rejected; and `.dockerignore` is in
the pull-request path filter. The focused shell suite proved that cleanup
failure turns a successful smoke nonzero, a pre-existing smoke failure remains
authoritative, a diagnostic-publication failure does not replace that original
status, and teardown, verification, and image cleanup are all attempted.

Gitleaks `v8.30.1` found no leaks in every technical-correction file, the
technical commit, or the complete pull-request commit range. The implementation
head's GitHub `Secret Scan (Gitleaks)` check also passed.

## Shutdown and cleanup

The gate stopped the service through `docker stop --time 20`, which sends the
normal SIGTERM path. The application exited with code `0`, was not OOM-killed,
did not restart, and did not require SIGKILL. Exit `137` is an explicit gate
failure. Cleanup always attempts Compose teardown, project-resource
verification, and temporary image removal. The original smoke failure remains
authoritative; if the runtime checks succeed but cleanup fails, the final result
is nonzero. The script emits its success line only after it proves that no
Compose container, labeled network or volume, or temporary image tag remains.
The override file, private raw diagnostics, and temporary directory are removed
on the cleanup path.

The authoritative job completed this cleanup path successfully. Its final line
reported shutdown exit `0`; the diagnostic verification and upload steps were
correctly skipped because the smoke itself succeeded.

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
- Node runtime/static smoke validators: 8 passed locally and on the authoritative Ubuntu job.
- Focused cleanup status tests: passed locally and on the authoritative Ubuntu job.
- Docker workflow path-trigger assertion: passed; `.dockerignore` is a pull-request trigger.
- Focused Python writable-path tests: 2 passed.
- Python prompt Runtime Truth table: 5 passed.
- `cargo fmt -- --check`: passed.
- `cargo test --locked --all`: 145 passed.
- `cargo clippy --locked --all-targets --all-features -- -D warnings`: passed.
- `git diff --check`: passed.
- All required implementation-head checks passed: public demo/audit packaging,
  full runtime stack, Python, security/public-boundary, frontend,
  JavaScript/Python build, Rust tests, GitHub Gitleaks, clippy, dependency/runtime
  audit, and JavaScript/TypeScript/Python CodeQL.

## Checks not performed and residual limitations

No real provider call, provider credential, billable request, hostile-traffic
validation, multi-instance validation, production deployment, target-platform
secret-management validation, WAF validation, penetration test, regional
failover test, or production monitoring/incident-response validation was
performed. The rate limiter, circuit breaker, and relevant runtime state remain
process-local. The demo Compose profile remains a controlled-demo profile, not
a production deployment profile.

A successful GitHub-hosted runner smoke test proves that the controlled-demo
image built and executed under the tested CI environment. It does not prove
production readiness, hostile-traffic resistance, multi-instance behavior,
target-platform secret management, or target-platform deployment health.

Final review and merge remain manual and exclusive to the repository owner. The pull request remains draft; no merge or auto-merge was performed.

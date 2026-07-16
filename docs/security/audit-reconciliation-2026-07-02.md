# Audit Reconciliation — 2026-07-02

> Historical configuration note: Any `OMINI_*` names below are preserved only as immutable audit evidence. They are obsolete and are not accepted by the current runtime, which recognizes only `OMNI_*` configuration.

## 1. Scope

This document reconciles the security audit findings reviewed on 2026-07-02 against the current `main` state and the hardening implemented in this PR.

The goal is to correct confirmed findings without weakening existing runtime governance, BYOK behavior, public payload sanitization, redaction, or CI security checks.

## 2. Confirmed false or stale findings

- The Python CVE table was based on dependencies not present in the current `backend/python/requirements.txt`; current verification must use `pip-audit` against the checked-in requirements.
- The alleged `execution.py` `exec()` finding was not confirmed in current `main`.
- The alleged `vm.runInNewContext` finding is not present in current `js-runner/queryEngineRunner.js`.
- The "no CI/CD" finding is false; the repository has GitHub Actions workflows, including security checks.
- The "empty security tests" finding is false; `tests/security/security-regression-suite.mjs` runs real regression checks.
- The "no observability auth" finding is false for `/api/observability/*`; those routes are protected by Supabase JWT or observability stream ticket middleware.

## 3. Confirmed real findings

- `/internal/*` routes lacked auth middleware.
- CORS used a permissive configuration that was too broad for production.
- The Docker runtime image did not switch to a non-root user.
- Agent memory should be opt-in and blocked in public/demo mode.
- Dependency audits needed a clearer blocking policy for PRs and `main`.

## 4. Fixes implemented in this PR

- Moved `/internal/runtime-signals`, `/internal/swarm-log`, `/internal/strategy-state`, `/internal/milestones`, and `/internal/pr-summaries` into a protected internal router using Supabase auth middleware.
- Replaced unconditional permissive CORS with an allowlist configuration using `OMNI_ALLOWED_ORIGINS` as the canonical variable and `OMINI_ALLOWED_ORIGINS` as a legacy alias.
- Kept local developer compatibility for `http://localhost:5173`, `http://localhost:3000`, and `http://127.0.0.1:5173` only in local/demo modes.
- Preserved a restrictive/fail-closed production CORS posture when no allowed origins are configured.
- Hardened the Docker runtime stage with a non-root `omni` user and ownership for `/app` and `/opt/venv`.
- Made agent-memory loading opt-in with `OMNI_ENABLE_AGENT_MEMORY=true` and blocked it in `OMNI_PUBLIC_DEMO_MODE` or `OMINI_PUBLIC_DEMO_MODE`.
- Extended `npm run test:security` to cover internal route auth, CORS configuration, agent-memory hardening, and Dockerfile non-root validation.
- Updated the security workflow so high/critical Node audit findings block PR/main, pip-audit is blocking where it can verify dependencies, and cargo-audit findings block when the tool installs successfully.
- Added a targeted Gitleaks allowlist for existing redaction and credential-store test fixture paths only; production paths remain covered by the default rules.

## 5. Remaining verification requiring external scanners

Secret exposure must be verified with external scanners using redaction:

```bash
gitleaks detect --source . --redact --verbose
trufflehog git file://. --only-verified
```

Dependency findings must be verified with current advisory databases:

```bash
npm audit --audit-level=high
cd frontend && npm audit --audit-level=high
pip-audit
cd backend/rust && cargo audit
```

Do not manually invent CVEs or assert secret exposure without scanner evidence.

## 6. Validation commands

The required validation sequence for this PR is:

```bash
git diff --check
npm ci
cd frontend && npm ci && cd ..
npm run test:security
npm run test:js-runtime
npm run test:python:pytest
cd backend/rust
cargo fmt --check
cargo clippy -- -D warnings
cargo test
cd ../..
docker build -t omni-audit-hardening:local .
gitleaks detect --source . --redact --verbose
trufflehog git file://. --only-verified
```

`trufflehog` is required only when the scanner is available in the local or CI environment.

## 7. Residual risk

- CORS correctness still depends on deployment configuration of `OMNI_ALLOWED_ORIGINS` or the legacy `OMINI_ALLOWED_ORIGINS` alias.
- Supabase JWT enforcement depends on valid runtime Supabase auth configuration.
- Docker non-root execution should be revalidated in every deployment target after image rebuild.
- Agent memory remains available with explicit `OMNI_ENABLE_AGENT_MEMORY=true`; operators must keep that opt-in disabled for public/demo surfaces.
- The Gitleaks allowlist intentionally covers only known test/eval fixture paths; new production findings must not be allowlisted without separate review.
- Advisory databases change over time, so dependency and secret scanner results must be rerun close to merge.

## Follow-up after remote Security Checks

The first remote `Security Checks` run for PR #510 failed in two places:

- `Secret Scan (Gitleaks)` failed before scanning because `gitleaks/gitleaks-action@v3` requires `GITHUB_TOKEN` for pull request scans. The log did not report a secret finding, rule, file, or commit. The workflow now passes `GITHUB_TOKEN` and explicitly sets `GITLEAKS_CONFIG=.gitleaks.toml`.
- `Dependency & Runtime Audit` failed in `cargo audit` with `RUSTSEC-2023-0071`, `rsa 0.9.10`, "Marvin Attack: potential key recovery through timing sidechannels", severity 5.9 medium, with no fixed upgrade available. The dependency path was `omini-api -> jsonwebtoken 10.4.0 -> rsa 0.9.10`.

The Rust code only validates and creates Supabase JWTs with `Algorithm::HS256`. The `rsa` dependency is pulled by `jsonwebtoken`'s broad `rust_crypto` feature set, but the current runtime does not expose RSA verification or decryption paths: validation is created with `Algorithm::HS256` and constrained with `validation.algorithms = vec![Algorithm::HS256]`.

Two remediation options were tested:

- `jsonwebtoken` with only `hmac`/`sha2` removed `rsa`, but failed runtime tests because `jsonwebtoken` 10 requires exactly one process-level crypto provider feature.
- `jsonwebtoken` with `aws_lc_rs` removed `rsa`, but failed local Windows builds because `aws-lc-sys` required NASM/C toolchain behavior not available in this environment.

Because upstream reports no fixed `rsa` upgrade for `RUSTSEC-2023-0071`, this PR uses a narrow `cargo audit` ignore for only `RUSTSEC-2023-0071` in `backend/rust/.cargo/audit.toml`, with an inline justification tied to HS256-only use. This is not a broad ignore. The tracking requirement is this document plus the inline audit config; remove the ignore when `jsonwebtoken` exposes an HS256-only provider path that preserves local Windows and CI builds.

Commands executed during the follow-up:

```bash
gh run view 28605883552 --job 84825849454 --log
gh run view 28605883552 --job 84825849522 --log
gh api repos/gitleaks/gitleaks-action/contents/README.md?ref=v3
cd backend/rust && cargo tree -i rsa
cd backend/rust && cargo tree -e features -i jsonwebtoken
cd backend/rust && cargo update
cd backend/rust && cargo audit
```

No secret rotation was required from the remote Gitleaks failure because the job failed on missing action token configuration and did not report a redacted secret finding. The local Gitleaks scan must still pass before merge, and any future verified real secret finding must trigger rotation according to the provider's incident procedure.

Remaining risks after this follow-up:

- `RUSTSEC-2023-0071` remains present in the dependency graph but is ignored narrowly because the current runtime is HS256-only and no upstream fixed upgrade exists.
- The `backend/rust/.cargo/audit.toml` ignore must be revisited on every `jsonwebtoken` or Rust crypto dependency update.
- The remote Gitleaks job must be rerun by pushing this follow-up commit to confirm the action accepts the token/config settings.
- The PR should remain draft until the full remote `Security Checks` workflow is green.

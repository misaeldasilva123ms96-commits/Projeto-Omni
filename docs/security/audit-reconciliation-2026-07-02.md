# Audit Reconciliation — 2026-07-02

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

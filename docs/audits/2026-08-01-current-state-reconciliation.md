# Current-State Reconciliation — 2026-08-01

## 1. Executive summary

| Item | Evidence |
| --- | --- |
| Audited branch | `origin/main` |
| Audited commit | `3aa51f54a3d4522eaa7021658c736b0525034658` |
| Audit date | 2026-08-01 |
| Scope | Canonical status and limitations, principal runtime paths, manifests, workflow definitions, governance, architecture documentation, and major merged changes after PR #496 |
| Conclusion | Omni has substantial controlled-demo/research foundations, but production, unrestricted autonomy, training, and dormant protected-route claims remain unsupported. |
| Runtime behavior changed | No. This reconciliation changes documentation only. |

The former canonical status centered on PRs #490-#496 and no longer described
the merged repository accurately. This reconciliation restores a commit-bound
baseline while separating implemented behavior, dormant code, documentation-only
preparation, workflow definitions, and validations actually executed.

## 2. Methodology

Evidence was evaluated in this order: current implementation, merged PRs,
current tests and workflow definitions, governance and roadmap, focused
architecture documentation, then historical reports.

The audit used static inspection of the required Rust, Python, Node, frontend,
configuration, governance, architecture, and workflow files; current package
manifests; merged PR metadata and changed-file evidence after #496; and the
documentation-safe commands recorded below. The principal Python orchestration
and bridge paths were inspected, but this was not a line-by-line audit of the
entire repository.

## 3. Claim validation matrix

| Claim | Previous documentation/report statement | Current evidence | Result | Required correction |
| --- | --- | --- | --- | --- |
| Frontend React version | React 18-era descriptions remained in historical material. | `frontend/package.json` specifies React and React DOM 19.2.7. | Outdated | Record React 19. |
| TypeScript version | TypeScript 5.6-era descriptions remained in historical material. | `frontend/package.json` specifies TypeScript 7.0.2. | Outdated | Record TypeScript 7. |
| Frontend dependency scope | Could be read as a minimal React/Supabase interface. | Manifest and source expose Zustand, Recharts, Framer Motion, Tailwind/PostCSS, Vite, Vitest, Testing Library, and multiple Cockpit surfaces. | Incorrect | Summarize the architecturally relevant runtime, state, charting, animation, styling, build, and test foundations. |
| Workflow count/categories | Older summaries implied only a small CI set. | `.github/workflows` contains 23 YAML definitions covering general CI, language/runtime lanes, security/dependency audit, Docker, demo/E2E, docs/lint, deployment/release, post-merge/manual validation, training, health, and automation. | Outdated | Inventory categories and separate existence from run success. |
| Python runtime accessibility | Historical reporting said critical Python runtime files were inaccessible. | `backend/python/brain/runtime/orchestrator.py` and related public bridge/configuration code are present and inspectable. | Incorrect | Describe inspected behavior without claiming a complete Python audit. |
| Canonical runtime modes | Status presented only a reduced/high-level subset. | `docs/architecture/runtime-modes.md` defines eleven named mode entries, including the partial alias pair. | Outdated | Preserve the complete canonical mode list and its evidence semantics. |
| Docker validation | Historical Docker results could appear current. | No daemon-backed image build or runtime smoke was executed for this reconciliation. | Not dynamically verified | Keep target-environment Docker validation as an active limitation. |
| Rate limiter scope | Public-traffic limitation described process-local enforcement. | Rust stores client windows in an in-memory `Mutex<HashMap<...>>` owned by application state. | Confirmed | Retain the multi-instance/edge limitation. |
| Circuit-breaker scope | Runtime limitation described process-local breaker state. | Rust runtime configuration/state keeps breaker state in-process. | Confirmed | Retain shared-state and restart limitations. |
| Threat-model availability | Older broad statements could imply no threat models exist. | Focused sandbox and MCP-vault threat models exist under `docs/security`, both marked draft/planning. No consolidated current system-wide model was identified. | Partially correct | Acknowledge focused drafts while retaining the consolidated-model gap. |
| No-auto-merge governance | Merge remains manual and owner-controlled. | `GOVERNANCE.md` forbids automatic merge/direct main publication. | Confirmed | Preserve this boundary. |
| Production readiness | Controlled-demo/research, not production-ready. | Process-local controls, deployment responsibilities, dormant routes, and unverified target/runtime behavior remain. | Confirmed | Preserve the honest classification. |

## 4. Recent repository evolution

### Implemented runtime, security, frontend, and infrastructure

- #510 added broad runtime/security hardening, secret scanning, Docker and test
  updates.
- #529 added the capability-source foundation and database migration without
  exposing the protected historical route.
- #532 stabilized frontend tests; #533-#545 delivered broader runtime, memory,
  provider, naming, security, CI/live-contract, health-signal, environment-alias,
  and multi-runtime hardening.
- #559 added an isolated Supabase capability-grant adapter; it remains private
  and dormant without `AppState` or router integration.
- #560 and #564 strengthened demo authentication, sandbox/path boundaries,
  security coverage, dependency remediation, and CI.
- #598 tightened JWT not-before rejection; #599 aligned the Node 24.15 baseline
  across applicable manifests/workflows.

### Documentation, design, and preparation

- #497 refreshed documentation after the former baseline.
- #513-#516, #530-#531, #543, #546, and #600 are governance, design-review,
  roadmap, status, or implementation-preparation documentation. They describe
  constraints and future work; they do not themselves enable runtime behavior.

### Disabled, dormant, or non-runtime work

- #512 introduced a protected historical-audit route skeleton with guards and
  tests, but `main.rs` does not wire its router and no endpoint is exposed.
- The #529 capability foundation/migration and #559 adapter support future
  integration but do not establish production database provisioning or route
  availability.
- Dependency-only PRs after #496 maintain Rust/JavaScript/frontend/mobile and CI
  baselines; they are not new product capabilities.

## 5. Active limitations

- Rust rate limiting and circuit-breaker state are process-local.
- Cross-replica coordination, distributed backpressure, shared health/failover,
  and production multi-instance operation are not proven.
- Docker build/runtime behavior and target-platform secrets handling were not
  dynamically validated here.
- WAF/edge controls, distributed observability, retention, alerting, quotas,
  backups, and incident response remain deployment responsibilities.
- External-provider reliability, billing/quotas, and live execution were not
  proven.
- The protected historical-audit route and Supabase adapter remain dormant and
  expose no endpoint.
- Focused threat models are drafts; no consolidated current system-wide threat
  model was identified.
- Autonomous actions and training remain governed/restricted; no unrestricted
  execution, self-rewrite, automatic training, or automatic merge is authorized.

## 6. Validation evidence

| Command | Result | Relevant output / failure |
| --- | --- | --- |
| `git diff --check` | Passed after correction | The first run identified trailing whitespace in two edited headings; it was removed. The rerun returned no diff errors. |
| `npm ci` | Passed with environment warning | Installed 17 packages, audited 18, and found 0 vulnerabilities. npm warned that local Node 24.14.1 is below the manifest requirement `>=24.15 <25`; installation still exited 0. No manifest or lockfile changed. |
| `npm run validate:audit-pack` | Passed after correction | The first run failed because rewritten limitations headings did not retain the validator's exact required section names. The canonical headings/phrases were restored; rerun reported `ok: true`, 7 documents and 29 sections checked. |
| `npm run validate:public-demo` | Passed | Reported `ok: true`, 9 files, 11 demo environment names, and 15 `.dockerignore` entries checked. This is static validation, not Docker runtime evidence. |
| `npm run validate:env-aliases` | Passed | Reported 0 active obsolete references, 192 canonical names, and the `OMNI_*`-only runtime policy. Historical and negative-test references remained classified separately. |
| Documentation/link validation | Not available | No dedicated Markdown/link validator script was found. The docs workflow only lists and uploads `docs/`; it does not validate links. |
| Gitleaks on each changed document | Passed | Gitleaks 8.30.1 reported no leaks in all three changed documents. |
| Gitleaks complete branch/repository history | Passed | `gitleaks git . --config .gitleaks.toml --redact --no-banner --log-opts='--all'` scanned 854 commits (about 19.40 MB) and reported no leaks. |
| Gitleaks `origin/main...HEAD` committed diff | Passed | Scanned the one-commit branch range (about 22.68 KB) and reported no leaks. |
| Diff scope gate | Passed | `git diff --name-only origin/main...HEAD` matched exactly the two updated canonical documents and the new reconciliation report; `git diff --check origin/main...HEAD` returned no errors. |

### Skipped dynamic checks

- Broad Rust, Python, JavaScript, frontend, and live-E2E suites are outside this
  documentation-only correction unless a documentation validator invokes them.
- Docker image build and full runtime smoke are not part of this documentation
  validation and require a daemon/target environment.
- Live external-provider calls are excluded to avoid credentials, billing, and
  network-dependent claims.

## 7. Residual uncertainty

This reconciliation does not prove penetration resistance, hostile public
traffic behavior, production multi-instance behavior, external-provider billing
or reliability, target-platform secret handling, full Docker runtime behavior,
or every deployment workflow. It is not a complete manual review of every
repository file, every historical PR, or every transitive dependency. Workflow
definitions are inventoried separately from the current GitHub Actions results.

No runtime, backend, frontend, provider, tool, autonomy, database, dependency,
lockfile, environment, or workflow behavior was changed by this audit.

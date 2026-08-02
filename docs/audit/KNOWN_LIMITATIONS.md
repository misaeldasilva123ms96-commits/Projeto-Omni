# Known Limitations

**Evidence date:** 2026-08-01

**Audited branch:** `origin/main`

**Audited commit:** `3aa51f54a3d4522eaa7021658c736b0525034658`

Only limitations supported by audited evidence are retained here, including
current implementation, configuration, workflow definitions, explicitly scoped
validation, governance documents, and focused security or threat-model
documentation. Historical reports do not override the audited implementation
or the commit-bound evidence recorded here.

## Release and deployment status

Omni is a controlled-demo/research system, not a production-ready autonomous
platform. There is no production release. This reconciliation does not authorize a public
deployment, tag, merge, training run, or autonomous action.

The repository includes deployment, release, Docker, health, public-demo, and
live-E2E workflow definitions. Their existence is not evidence of a currently
healthy deployment or a successful run at the audited commit.

## Public Traffic

The Rust chat rate limiter stores counters in process memory. Circuit-breaker
state is also process-local. Neither provides shared enforcement or coordinated
state across replicas, restarts, or regions. Hostile public traffic and
multi-instance deployments require edge/platform rate limiting and shared
operational controls.

The trusted-proxy and bounded-client-map hardening was subsequently verified at
technical commit `f70d209998e315b1e63dd8ceffdf1560c8a8c2aa`. Direct chat
requests now use the actual TCP peer IP instead of a shared `global` bucket.
`X-Forwarded-For` can influence identity only when the immediate peer belongs
to deployment-specific `OMNI_TRUSTED_PROXY_CIDRS`; `Forwarded` and
`X-Real-IP` remain intentionally ignored. Invalid proxy configuration fails
startup, malformed chains fall back to the peer, and a full active bucket map
rejects new identities without evicting active clients. Commit-bound local and
remote evidence is recorded in
[`docs/audits/2026-08-02-trusted-proxy-rate-limit-hardening.md`](../audits/2026-08-02-trusted-proxy-rate-limit-hardening.md).

This does not make the limiter distributed or the deployment production-ready.
It remains process-local, resets on restart, and requires edge/platform
enforcement for replicas. Proxy CIDRs must be configured for each deployment.
No WAF, hostile internet traffic, production deployment, multi-instance
coordination, distributed rate-limit store, or penetration test was validated.

## Runtime Scope

Subprocess remains the default runtime path. Python and Node service modes are
opt-in. Cross-process lifecycle management, shared health state, distributed
backpressure, coordinated failover, and multi-instance behavior are not proven
production-complete.

The Python-to-Node boundary was subsequently hardened at authoritative
technical head `a6f6b34e79f560e9dfc71455d1ef63ab893c96f7`. Runner, policy module,
schema, adapter, engine,
cwd, environment, and memory paths now use an explicit canonical-root policy
with independent Python and JavaScript validation. Security-sensitive symlinks,
Windows junctions/reparse points, traversal, unsafe file types, mutable-plan
tampering, reserved overlay keys, `NODE_OPTIONS`, and `NODE_PATH` fail closed.
The final correction adds a built-in-only bootstrap before either JavaScript
entrypoint loads `pathPolicy.js` and validates `fusionBrain.js` before any
adapter import. Earlier implementation evidence did not cover those two gaps.
Commit-bound evidence is recorded in
[`docs/audits/2026-08-02-node-runner-path-containment.md`](../audits/2026-08-02-node-runner-path-containment.md).

This remains application-level validation, not an OS sandbox. Node/Bun may be
installed outside the project. A privileged local actor and filesystem-write
TOCTOU replacement remain outside the complete guarantee. No seccomp,
AppArmor, SELinux, production deployment, hostile multi-user host,
penetration-test, or distributed runtime-isolation validation was added.

## Docker Validation

No daemon-backed Docker build or full container runtime smoke was executed in
the historical 2026-08-01 reconciliation. That historical scope remains
unchanged.

A GitHub-hosted CI runtime smoke was subsequently verified at implementation
commit `d9a0be591c52645aa3bf08f03b9f72a6340f1340` in
[Actions run 30731215303](https://github.com/misaeldasilva123ms96-commits/Projeto-Omni/actions/runs/30731215303).
The tested controlled-demo image built, became healthy, served health/status/chat,
preserved Runtime Truth and request boundaries, enforced its effective container
hardening, passed fail-closed diagnostic-publication and synthetic-secret
leakage checks, verified final cleanup, and exited normally through the tested
SIGTERM path. The commit-bound details are recorded in
[`docs/audits/2026-08-02-docker-runtime-smoke.md`](../audits/2026-08-02-docker-runtime-smoke.md).

The target deployment environment remains unverified. Target deployment Docker image build still needs daemon-backed validation. A production container profile
remains nonexistent or unverified. Hostile traffic, multi-instance
behavior, target-platform secret management, and target-platform deployment
health remain unverified. Static validation and GitHub-hosted runner evidence do
not establish any of those properties.

The demo container profile is not a production deployment profile. WAF/edge
controls, secret injection and rotation, distributed monitoring, retention,
backups, provider quotas, alerting, and incident response remain deployment
responsibilities.

## Providers

Provider discovery, routing, provenance, and adapters do not prove live external
availability or successful model execution. Real-provider billing/quota APIs
are not integrated as production accounting. Credentials, billing, rate limits,
regional availability, latency, and reliability must be validated in the target
environment without exposing secrets.

## Historical-audit and autonomy surfaces

The protected historical-audit router, capability resolver foundations, and
isolated Supabase capability adapter exist in the repository, but the route is
disabled/dormant: it is not integrated into `AppState`, not wired by `main.rs`,
and exposes no endpoint. Async resolver integration is still preparation work.

Autonomous capabilities remain governed and allow-listed. The repository does
not authorize unrestricted tool execution, caller-supplied privilege claims,
self-modification, automatic merge, or unattended production actions.

## Security assurance

Focused sandbox and MCP-vault threat models exist, but both are draft/planning
documents. A consolidated, current, system-wide threat model was not identified.
This documentation audit is not a penetration test, hostile-traffic exercise,
red-team assessment, or complete manual security review.

Repository controls do not replace production WAF, identity, secret-management,
network, audit-retention, and incident-response controls.

## Training

No training was started and no production dataset was produced by this audit.
Learning signals are advisory. Export remains subject to redaction, governance,
runtime-mode, fallback, tool, and provider-failure gates. The existence of the
training workflow does not authorize or prove a training run.

Historical logs are not retroactively rewritten. Hardening and redaction apply
to the paths that use those controls after their introduction.

## Validation scope

The reconciliation report records exactly which static validators, installation
steps, diff checks, and secret scans were executed. It does not imply that broad
Rust/Python/JavaScript suites, live providers, Docker runtime, production
multi-instance behavior, or every workflow were dynamically validated.

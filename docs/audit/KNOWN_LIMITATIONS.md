# Known Limitations

**Evidence date:** 2026-08-01

**Audited branch:** `origin/main`

**Audited commit:** `3aa51f54a3d4522eaa7021658c736b0525034658`

Only limitations supported by the audited implementation, configuration,
workflow definitions, or explicitly scoped validation are retained here.
Historical reports do not override current code.

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

## Runtime Scope

Subprocess remains the default runtime path. Python and Node service modes are
opt-in. Cross-process lifecycle management, shared health state, distributed
backpressure, coordinated failover, and multi-instance behavior are not proven
production-complete.

## Docker Validation

Docker image build still needs daemon-backed validation. No daemon-backed Docker
build or full container runtime smoke was executed in the 2026-08-01
reconciliation. Static validators do not prove that the image
starts, serves `/health`, accepts `/chat`, or preserves runtime policies on the
target platform. A controlled deployment still needs image build, container
startup, health/chat smoke, shutdown, and target-environment evidence.

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

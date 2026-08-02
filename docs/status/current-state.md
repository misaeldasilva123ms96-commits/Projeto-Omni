# Omni Current State

**Evidence date:** 2026-08-01

**Audited branch:** `origin/main`

**Audited commit:** `3aa51f54a3d4522eaa7021658c736b0525034658`

**Classification:** controlled-demo/research system; not production-ready autonomous infrastructure.

This page describes merged repository state. A workflow, test, adapter, route, or
design document is not evidence that the corresponding production capability is
deployed, enabled, or operational.

## Implemented foundations

| Area | Current merged state |
| --- | --- |
| Rust API | Axum HTTP boundary, authentication and public-payload controls, subprocess/service bridge selection, run control, observability, and process-local resilience controls. |
| Python Brain runtime | Publicly inspectable orchestration, governance, sanitization, runtime classification, provenance, memory/learning signals, provider configuration, and Node bridge logic. This reconciliation inspected the principal runtime path, not every Python file. |
| Node QueryEngine runtime | Provider selection/provenance, matcher and direct-response lanes, governed tool/action foundations, runtime-truth emission, and subprocess/service entry points. |
| Runtime Truth | Explicit modes, reasons, fallback state, provider/tool evidence, execution lanes, provenance, and diagnostics. Transport success alone is never cognitive success. |
| Provider routing | Remote adapters for Groq, OpenRouter, OpenAI, Anthropic, and Gemini; configured local Ollama and LM Studio adapters; local heuristic fallback. DeepSeek is metadata-only and non-executable. Selection does not prove attempted or successful provider execution. |
| Frontend | React 19 Cockpit built with TypeScript 7 and Vite 8, with Zustand state, Recharts visualization, Framer Motion, Tailwind/PostCSS styling, and Vitest/Testing Library test foundations. It includes chat, Runtime Truth/Inspector, provider, governance, memory, agent, project, observability, token-use, history, and lab surfaces. |
| Security | Authentication and JWT hardening, public payload and demo boundaries, path-containment and regex hardening, Gitleaks/security workflows, focused draft threat models, and regression tests. Deployment-edge controls remain external responsibilities. |
| Autonomy and audit | Governed gateway and dry-run/historical-audit foundations exist. The protected historical-audit router and isolated Supabase capability adapter are dormant: they are not in `AppState`, not wired into the main router, and expose no endpoint. Later async-resolver work is preparation documentation, not runtime integration. |
| Database | Supabase-oriented schema/migration foundations exist, including capability-grant storage. Their presence does not establish production provisioning or route exposure. |
| Learning/training | Advisory learning signals, schemas, validation, dry-run export policy, and a training-pipeline workflow definition exist. No uncontrolled self-rewrite, automatic training, or unrestricted training export is authorized. |
| Governance | Manual owner review, no direct pushes to `main`, no automatic merge, explicit capability boundaries, and documentation/runtime-truth requirements. |

## Default runtime path

```text
Rust/Axum HTTP API
  -> Python subprocess BrainOrchestrator
  -> Node subprocess QueryEngine runner
  -> Python public-payload sanitization
  -> Rust HTTP response
```

Python and Node service modes are opt-in. Subprocess execution and Node are the
default contributor path; Bun is opt-in. Service lifecycle, shared resilience
state, and multi-instance coordination are not production-complete.

## Canonical runtime modes

The canonical modes are:

- `FULL_COGNITIVE_RUNTIME`;
- `PARTIAL_COGNITIVE_RUNTIME` / `PARTIAL_COGNITIVE`;
- `NODE_EXECUTION_SUCCESS`;
- `LOCAL_TOOL_SUCCESS`;
- `MATCHER_SHORTCUT`;
- `DIRECT_LOCAL_RESPONSE`;
- `SAFE_FALLBACK`;
- `SAFE_DEGRADED_FALLBACK`;
- `NODE_FAILURE`;
- `PROVIDER_FAILURE`;
- `COMPATIBILITY_EXECUTION`.

Their evidence requirements are defined in
[`docs/architecture/runtime-modes.md`](../architecture/runtime-modes.md).
HTTP 200, valid JSON, `status=success`, or `NODE_EXECUTION_SUCCESS` alone do not
prove full cognitive execution. Provider selected is not provider attempted;
tool planned is not tool executed.

## Workflow inventory

At the audited commit, `.github/workflows` contains 23 workflow definitions.
They cover general CI, frontend, Node, Python, Rust, runtime, security and
dependency audit, Docker, public demo, live E2E, documentation deployment, lint
and static checks, deployment, release, post-merge validation, manual full
validation, training, health checks, and repository automation.

This inventory proves that workflow definitions exist. It does not prove that
every workflow ran or succeeded for this commit; current run evidence must be
reported separately.

## Evolution after PR #496

Major merged changes after the earlier #490-#496 baseline include:

- documentation refresh and governance/design/preparation cycles (#497,
  #513-#516, #530-#531, #543, #546, and #600);
- runtime and security hardening, including public-demo boundaries, canonical
  environment naming, cognitive routing, JWT validation, provider health, and
  multi-runtime resilience (#510, #533-#545, #560, #564, and #598-#599);
- frontend test stabilization and runtime/provider visibility work (#532,
  #541, and portions of the broader hardening cycles);
- a protected historical-audit route skeleton (#512), capability-source and
  migration foundations (#529), and an isolated Supabase grant adapter (#559),
  all preserved without main-router endpoint exposure;
- dependency maintenance across Rust, JavaScript, frontend/mobile, and CI
  baselines, including the Node 24.15 compatibility cycle.

Documentation-only preparation and dormant implementations in those PRs must
not be reported as enabled runtime capability.

## Threat-model and security status

Focused threat models exist for the sandbox and MCP vault under
`docs/security/`. Both are draft/planning documents and do not prove all
described controls are implemented. No consolidated, current, system-wide
threat model was identified in this audit. Implemented controls must be traced
to code, tests, and workflow evidence independently.

## Active boundaries and limitations

- Rate limiting and circuit-breaker state are process-local; they do not
  coordinate across replicas.
- Full Docker image/runtime smoke was not executed for this reconciliation and
  still needs target-environment validation.
- WAF/edge rate limiting, production secret management, distributed telemetry,
  retention, quotas, and incident response remain deployment responsibilities.
- Real external-provider availability, reliability, billing, and quota
  integration are not proven by configuration or static inspection.
- Protected historical-audit capability work remains disabled/dormant and no
  endpoint is exposed by the main router.
- Autonomous actions remain allow-listed and governed; unrestricted tool use,
  self-modification, automatic merge, and automatic production action are not
  authorized.
- Training remains restricted to governed preparation/dry-run paths. This audit
  did not start training or produce a production dataset.
- The repository is suitable for controlled demonstration and research, not a
  production readiness claim.

See [`docs/audit/KNOWN_LIMITATIONS.md`](../audit/KNOWN_LIMITATIONS.md) for the
active limitations and
[`docs/audits/2026-08-01-current-state-reconciliation.md`](../audits/2026-08-01-current-state-reconciliation.md)
for evidence and validation scope.

## Documentation authority

For claims made by this current-state page, use this order:

1. Current implementation at audited commit
   `3aa51f54a3d4522eaa7021658c736b0525034658`.
2. Merged pull-request evidence, tests, and workflow definitions included in
   that audited commit.
3. `GOVERNANCE.md` as present at the audited commit.
4. `ROADMAP.md` as present at the audited commit.
5. This canonical current-state page and focused architecture documentation.
6. Historical reports and superseded planning documents.

When `main` advances beyond the audited commit, this page must be refreshed
through a new evidence-based reconciliation before it is treated as describing
the newer repository state.

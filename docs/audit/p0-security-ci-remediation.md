# P0 security, sandbox, Python CI, and test isolation remediation

Date: 2026-07-20

Branch: `codex/fix-p0-audit-security-ci-hardening`

Base: `origin/main` at `e5430af98b9a46a7a686f053a3aa898e67612daa`

## Status and evidence classification

This document distinguishes runtime reproduction, code inspection, verified correction,
and residual risk. A green targeted test is not treated as proof that an unexecuted full
suite passed.

| Finding | Baseline evidence | Remediation | Current classification |
| --- | --- | --- | --- |
| Static demo JWT secret | The public-demo configuration path selected a repository-known HS256 secret and predictable issuer. Protected routers were merged into the application. The initial end-to-end reproduction build did not complete inside the first ten-minute window. | Authentication now requires an explicit `SUPABASE_JWT_SECRET` of at least 32 bytes and a clean HTTPS Supabase project base URL. URL parsing rejects missing hosts, credentials, paths, query strings, fragments, non-HTTPS schemes, and ambiguous malformed forms. Public-demo mode grants no authentication configuration. Route-level regression rejects a token signed with the historical material while all other claims remain valid. | Code-level risk confirmed; fixed and verified after implementation. Pre-fix end-to-end exploitability was not established. |
| Sandbox root escapes | `Path(__file__).resolve().parents[6]` resolved to the worktree container in the isolated checkout, so a sibling worktree was inside the calculated boundary. Safe temporary directories outside the repository were also accepted. Path-valued flags were skipped because every dash-prefixed argument was ignored. | The root is explicit or marker-discovered, validated, and threaded through command validation. Exact resolved containment rejects parents, siblings, symlink escapes, home, filesystem roots, relative/nonexistent roots, and Windows case variants. Supported pytest and Cargo path flags are parsed in equals and separated forms; unknown security-sensitive path flags fail closed. | Independently reproduced; fixed and verified. |
| Incomplete Python CI | Default collection covered only `backend/python/tests`; the broader `tests` tree was omitted. Test dependencies were installed ad hoc and `asyncio_mode` had no declared executor in the baseline environment. | A canonical runner invokes both trees in separate processes, always aggregates both exit codes, declares the complete test dependency set, and is used by pre-merge and validation workflows. | Fixed at repository-command level; full execution exposes the broader legacy failure inventory listed below. |
| Persistent test state | A direct async suite changed tracked files under `backend/python/memory`. Several runtime tests used `.phase9-temp` in the checkout. | Canonical and direct pytest runs receive per-session memory, cache, database, artifact, log, credential, session, upload, home, temp, and XDG roots. The root hook snapshots every environment key it mutates or removes and restores the caller environment after success, test failure, or cleanup failure. The canonical runner starts from an explicit host-environment allowlist. | Independently reproduced; fixed for the exercised paths and guarded by contract tests plus before/after Git status comparison. |
| Main branch protection | GitHub returned `404 Branch not protected` for `main` on 2026-07-20. | Stable workflow/job names are defined below. Repository settings were intentionally not mutated by the agent. | Pending repository-owner action. |

## Authentication behavior

Protected routes remain registered, but application startup now fails closed when secure
authentication configuration is missing or too short. `PUBLIC_DEMO_MODE` does not supply
credentials, bypass validation, or imply authorization.

Tests cover:

- missing configuration in public-demo mode;
- accepted explicit high-entropy configuration;
- wrong issuer;
- wrong signature;
- rejection of the historical demo-key material by `/internal/runtime-signals`.

The historical secret and complete forged token are not printed in test output or this
report.

## Sandbox boundary

Root resolution order:

1. the explicit `workspace_root` on the command request;
2. `OMNI_WORKSPACE_ROOT`, if configured;
3. an ancestor of the sandbox module containing repository markers.

The resolved root must be an existing absolute directory, must contain repository markers,
and cannot equal the filesystem root or user home. Every requested working directory and
path-like argument must resolve inside that exact root via `Path.relative_to`. Subprocesses
do not inherit developer `HOME`, `USERPROFILE`, `TEMP`, or `TMP`.

Supported path-valued command flags are explicit: pytest accepts `--basetemp`,
`--rootdir`, `--config-file`, and `-c`; Cargo accepts `--manifest-path` for the
already-allowed `check`, `test`, and `clippy` commands. Both `--flag=value` and
`--flag value` forms pass through the same normalized containment check. Other
security-sensitive path flags are rejected rather than treated as ordinary options.

## Canonical Python test contract

Commands:

```text
npm run test:python:backend
npm run test:python:runtime
npm run test:python:all
npm run test:python:coverage
```

`test:python:all` launches both suites in separate pytest processes even if the first
fails. Its result is nonzero if either suite fails. The runner snapshots
`git status --porcelain=v1` before and after execution and treats any change as a test
failure. `backend/python/requirements-test.txt` is the single declared installation input
for runtime and test dependencies, including `pytest-asyncio`, `pytest-cov`, and
`hypothesis`.

`test:python:coverage` runs the same backend and runtime suites through the same isolated
runner, combines their measurements in `.tmp/python-coverage/.coverage`, prints a report,
enforces the `.coveragerc` threshold of 40%, and writes
`.tmp/python-coverage/coverage.xml`. Any suite failure, missing coverage data, report
failure, XML-generation failure, or threshold miss returns a nonzero status.

## CI and main protection

The workflow inventory is:

| Workflow | Job | Installs canonical dependencies | Backend suite | Runtime suite | Aggregate command | Timing | Required-check candidate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CI` | `build-and-test-js-python (24.x, 3.11)` | Yes | No | No | None | Pull request and `main` push | No, not a Python-suite gate |
| `Omni Python CI` | `Python All Tests` | Yes | Yes | Yes | `test:python:all` | Pull request/manual | Yes; stable pre-merge Python gate |
| `Omni Runtime CI` | `Full runtime stack` | Yes | Yes | Yes, plus a focused runtime/performance rerun | `test:python:all` | Pull request, selected pushes, manual | Yes, broader duplicate validation |
| `Omni Security CI` | `Security and public-boundary regression` | Yes | No | No | None | Pull request/manual | No, it runs `test:security` rather than pytest suites |
| `Manual Full Validation` | `Manual pre-merge full validation` | Yes | Yes | Yes | `test:python:all` | Manual pre-merge | Manual evidence, not an automatic required check |
| `Post-Merge Validation` | `Full validation` | Yes | Yes | Yes | `test:python:coverage` | `main` push/manual | Post-merge required coverage gate, not pre-merge |

Only `Omni Python CI`, `Omni Runtime CI`, and `Manual Full Validation` invoke the literal
`npm run test:python:all` command. Installing `requirements-test.txt` is not described as
suite execution. The combined `CI` job intentionally avoids another multi-hour duplicate;
`Python All Tests` remains the unambiguous pre-merge Python gate.

`Omni Python CI` no longer has path filters, so its stable job is present on every pull
request. The owner should protect `main` with these exact required checks after observing
one successful pull-request run:

```text
build-and-test-js-python (24.x, 3.11)
rust-tests
Python All Tests
Full runtime stack
Security and public-boundary regression
CodeQL JavaScript/TypeScript and Python
```

Recommended protection settings:

- require a pull request before merging;
- require one approving review and dismiss stale approvals;
- require approval of the most recent push;
- require conversation resolution;
- require the checks above to pass and require the branch to be up to date;
- prohibit force pushes and deletion;
- apply the rules to administrators;
- do not enable auto-merge for this remediation.

This configuration is pending repository-owner action. The agent did not change branch
protection and will not merge the pull request.

## Coverage decision

Coverage remains a required post-merge gate. The earlier post-merge command measured
`brain` and sandbox modules and inherited the 40% `.coveragerc` threshold, but the first
canonical-runner migration replaced it with plain pytest and therefore removed that
enforcement. `test:python:coverage` restores the threshold without bypassing either
canonical tree. It measures the configured language, control, observability,
orchestrator-services, and sandbox modules; emits terminal output and
`.tmp/python-coverage/coverage.xml`; and is blocking in `Post-Merge Validation`. The XML
file is uploaded as the `python-coverage` artifact even when the validation step fails.

## Network-isolation guarantee and follow-up

The current guarantee is deliberately limited: in-process Python `socket.connect` and
`connect_ex` calls made by tests are denied for non-loopback destinations, while loopback
remains available. Provider and credential environment variables are removed from direct
pytest and canonical-runner environments. This monkeypatch does **not** propagate into
Python, Node, curl, Git, provider-client, or other subprocesses, so subprocess egress is
not fully blocked.

Full subprocess isolation is deferred as a P1 infrastructure-hardening task because this
PR has to work on Windows developer hosts and GitHub-hosted Linux runners, and a pytest
hook cannot create a trustworthy cross-platform network boundary. The follow-up plan is:

1. Threat model subprocess DNS, TCP/UDP, proxy, Git transport, package-manager, and
   provider-client egress while preserving loopback integration tests.
2. Enforce the boundary outside pytest: a network-disabled Linux container or namespace
   is preferred in CI; Windows should use an isolated container or an owner-managed
   firewall policy rather than command-name interception.
3. Test Python, Node, curl, Git remote, and provider-client subprocesses against denied
   external endpoints plus allowed IPv4/IPv6 loopback servers.
4. Roll out first as an advisory dedicated job, then make it blocking after platform and
   local-integration compatibility is established.
5. Roll back by disabling only that dedicated infrastructure job/policy; retain the
   in-process socket guard and credential stripping.

## Full-suite residual failures

The follow-up canonical backend execution is green: 709 passed plus 20 subtests. The
canonical runtime execution reports 1,844 passed, 7 failed, 4 skipped, 133 subtests, and
3 warnings. All seven failures are in `tests/fusion/phase2_runtime_test.py` and exercise
the Rust/Cargo executor bridge. A representative failure was rerun directly outside the
Node canonical runner and still returned `rust_bridge_timeout`, so the failures are not
caused by the runner environment allowlist or aggregate logic.

`test:python:all` reproduces the same split: the backend tree passes, the runtime tree
returns the same seven failures, and the aggregate correctly returns nonzero. The coverage
command also preserves those failures while still producing its report: total measured
coverage is 87.13%, above the required 40%, and `coverage.xml` is written successfully.
The command returns nonzero because suite failures are never hidden by coverage success.

These pre-existing bridge failures keep the local overall remediation verdict at
`PARTIAL`. Resolving the executor-bridge cold-build/timeout behavior requires separate
runtime ownership and is not folded into this security follow-up.

## Security pattern review

| Pattern | Result |
| --- | --- |
| Default or hardcoded JWT secrets | Historical fallback removed; no equivalent auth fallback retained. |
| Predictable demo issuer authorization | Demo mode no longer creates an auth configuration. Explicit issuer validation remains. |
| Public-demo authorization shortcut | No authentication shortcut remains. |
| `parents[n]` workspace security boundary | Removed from the sandbox runner. Other uses must be classified by their own trust boundary. |
| String-prefix path containment | Sandbox uses resolved `Path.relative_to`, not string prefixes. |
| User-home sandbox root | Explicitly rejected. |
| Pytest command omitting a tree | Canonical all command runs both trees. |
| Workflow-local Python test dependencies | Replaced by `requirements-test.txt` in the affected workflows. |
| `asyncio_mode` without an executor | `pytest-asyncio` is declared. |
| Repository memory writes during tests | Reproduced, redirected, and guarded. |
| Real provider or Supabase access | Provider credentials are stripped. Non-loopback sockets are blocked only in the pytest process; subprocess egress remains an explicit P1 infrastructure risk. |
| Mutable GitHub Action references | Existing workflows still contain mutable version tags. Pinning all third-party actions is future supply-chain work because it is broader than the P0 correction. |

## BrainOrchestrator decomposition plan

Current evidence: `orchestrator.py` is approximately 7,332 lines. `BrainOrchestrator`
owns construction, turn handling, routing, planning, execution, run control, Node calls,
learning, memory, inspection events, JSONL persistence, and response synthesis. Many
methods read environment state or mutate instance-wide state.

### Proposed boundaries and state ownership

| Component | Responsibility | Owns state | Side effects and dependency direction | Risk |
| --- | --- | --- | --- | --- |
| `ExecutionContext` | Typed immutable snapshot of turn ID, paths, policy, capabilities, budget, session, and selected runtime mode. | Per-turn values only; immutable where practical. | Created at the composition root; lower layers receive it explicitly and never read global environment state. | Medium |
| `TurnContextBuilder` | Normalize input and assemble history, retrieved context, memory hints, capabilities, and budgets. | No long-lived mutable state. | Depends on narrow reader protocols; produces `ExecutionContext` and pure data for `DecisionPipeline`. | Medium |
| `DecisionPipeline` | Intent prediction, ranked routing, strategy selection, planning, and compatible fallback decisions. | No I/O state; deterministic decision inputs/outputs. | Depends on pure policy/ranking functions; calls no tools or persistence. | High |
| `ActionExecutionCoordinator` | Run-control clearance, graph/tree scheduling, action batches, execution, continuation, and result normalization. | Per-run execution state and cancellation/control handles. | Depends on executor ports and event sink; receives decisions but does not own learning or response presentation. | High |
| `LearningRecorder` | Evaluation, memory updates, reflection, summaries, engineering data, and sanitized persistence. | Writer handles and retention policy only. | Consumes completed result events; depends on memory/event-store ports. Never influences the in-flight action result. | Medium |
| `RuntimeInspectionEmitter` | Runtime-mode, selection, control, tool, and upgrade inspection events. | Sequence metadata and sink reference. | Write-only observer interface; callers do not depend on sink success for authorization or execution. | Low |

### Pure logic candidates

Move intent weighting, plan signatures, JSON redaction/normalization, graph readiness,
completion predicates, progress calculation, response extraction, failure classification,
and result-to-memory transformations into stateless functions first. Keep subprocesses,
files, provider calls, clocks, environment reads, run-control waits, and event persistence
behind explicit protocols.

### Migration order

1. Add characterization tests around `run`, primary-path dispatch, blocked actions,
   continuation, learning output, and inspection output.
2. Introduce typed frozen `ExecutionContext` plus adapters populated from the existing
   constructor. Keep the public `BrainOrchestrator` API unchanged.
3. Extract pure graph, normalization, ranking, and response helpers.
4. Extract `RuntimeInspectionEmitter`; use a no-op/test sink for unit tests.
5. Extract `TurnContextBuilder`, then `LearningRecorder`.
6. Extract `DecisionPipeline` behind a compatibility facade.
7. Extract `ActionExecutionCoordinator` last because it owns the highest-coupling path.
8. Reduce `BrainOrchestrator` to composition and compatibility delegation only after
   behavioral parity is proven.

### Compatibility, testing, and rollback

Preserve constructor, context-manager behavior, `run`, `resume_run`, metrics, event schema,
stop reasons, and response text contracts. Run old and new components in shadow comparison
for deterministic phases before switching one boundary at a time. Use fixture-based golden
events plus unit, contract, failure-injection, resume, concurrency, and end-to-end tests.
Each extraction is a separate commit and feature-switchable delegation; rollback reverts
only that delegation without changing stored schemas. Perform this work on
`refactor/brain-orchestrator-decomposition` in a separate PR.

## Rust `main.rs` modularization plan

Current evidence: `main.rs` is approximately 5,621 lines and contains configuration,
application state, request/response types, route construction, authentication composition,
settings handlers, public/internal/operator handlers, Python process/service bridge logic,
file readers, and a large test module.

### Proposed modules and dependency direction

| Module | Content and state ownership | Depends on | Risk |
| --- | --- | --- | --- |
| `config` | Validated environment-derived settings and fail-closed startup decisions. No router state. | Primitive parsing and error types only. | Medium |
| `app_state` | `AppState`, health/circuit state, stores, clients, and constructors. | `config` plus narrow component interfaces. | High |
| `public_contracts` | Stable serialized request/response DTOs and redaction-safe public errors. | No handlers or infrastructure. | Low |
| `auth` | Existing auth config, middleware composition, scopes, and protected-router policy. | `config`, auth stores, Axum middleware. | High |
| `python_bridge` | subprocess/service request creation, parsing, circuit policy, and failure mapping. | `config`, `app_state`, typed bridge contracts. | High |
| `chat` | chat validation, rate limiting, credential normalization, and public/private handlers. | `public_contracts`, `python_bridge`, `app_state`. | High |
| `router` | Public/protected route grouping, limits, CORS, layers, and final assembly. | handlers, `auth`, `app_state`; no environment reads. | High |
| `integration_tests` | Route-level auth, limits, public-contract, and bridge tests outside the binary source. | Public crate modules and test fixtures. | Medium |

`main.rs` should end with only tracing/config loading, dependency construction, router
assembly, listener startup, and graceful shutdown.

### Staged migration

1. Establish route inventory and snapshot tests for public, protected, and absent routes.
2. Move stable DTOs and pure validation/redaction helpers to `public_contracts`.
3. Move environment parsing to `config`, retaining identical defaults and startup errors.
4. Move Python bridge parsing and transport policy behind a typed interface.
5. Move chat/settings/operator/internal handlers by coherent route group.
6. Move auth and route composition together only after protected-route tests cover every
   group; preserve rate limits, request limits, CORS, scope checks, and middleware order.
7. Move `AppState` once consumers depend on module interfaces rather than binary-local
   symbols.
8. Move integration tests out of `main.rs`, then reduce the binary to composition.

Each stage preserves API paths, JSON shapes, status codes, runtime truth, auth rejection,
Python failure classes, rate limits, observability, and existing tests. Use route-level
negative tests, serialization snapshots, middleware-order tests, Python bridge fixtures,
and full Rust tests at every stage. Rollback is commit-by-commit; do not change persistence
schemas or route contracts in extraction commits. Perform this work on
`refactor/rust-main-modularization` in a separate PR.

## Owner manual verification

1. Review the draft PR and all recorded residual failures.
2. Confirm a deployment without secure auth configuration refuses startup when protected
   routes are present.
3. Confirm the historical demo-key request receives an authorization failure.
4. Run both canonical Python suites from a clean disposable checkout.
5. After the check names have appeared on the PR, configure the exact `main` protection
   policy above.
6. Merge manually only after required checks and review are satisfactory.

This remediation must not be merged automatically. The repository owner must review and
merge it manually.

# Production Readiness Gates

This document defines measurable release gates for the Omni multi-runtime path. A release is not production-ready when any required gate is missing, skipped, inconclusive, or failing.

## Required CI Gates

| Gate | Required evidence | Pass criterion |
| --- | --- | --- |
| Runtime correctness | `omni-runtime-ci.yml` | Node, Python, Rust, security, lifecycle, retention, and performance tests all pass. |
| Live success path | `omni-live-e2e-ci.yml` | Rust → Python → Node → Rust returns `python_completed`, `FULL_COGNITIVE_RUNTIME`, and `fallback_triggered=false`. |
| Live failure path | `runtime-failure-contract.e2e.ts` | An unavailable Node process remains HTTP-controlled and reports explicit fallback with a `NODE_*` reason. |
| Dependency security | `security.yml` | npm, pip-audit, cargo-audit, Gitleaks, and CodeQL all complete successfully; tool installation failure is a failed gate. |
| Patch hygiene | `git diff --check` | No whitespace errors. |

## Runtime SLO Candidates

These thresholds are the initial production baseline and must be measured from the bounded runtime metrics window rather than inferred from single requests:

- `runtime_turn` latency: p95 at or below 45 seconds and p99 at or below 60 seconds.
- `node_boundary` latency: p99 must not exceed `OMNI_NODE_SUBPROCESS_TIMEOUT_SECONDS × 1000` plus 1 second of process overhead.
- Runtime truth: zero healthy-success classifications during injected Node failure tests.
- JSONL retention: the checked-in benchmark must process a file near 10 MB in under 15 seconds and rotate a file near 50 MB in under 8 seconds.
- Memory safety: latency series retain at most 2,048 samples per metric, and persisted chat history accepts at most 200 validated messages.

Percentile gates should be evaluated only after at least 100 production-like samples. A smaller window is diagnostic evidence, not an SLO pass.

## Lifecycle And Degradation Requirements

- Every short-lived `BrainOrchestrator` owner must call `close()` through `try/finally` or a context manager.
- Long-lived `TaskService` owners must close the service during application shutdown.
- Node circuit breaker states must be observable as closed, open, or half-open, and an open circuit must skip process creation.
- Mock chat is permitted only in local/demo environments unless `OMNI_ALLOW_MOCK_CHAT` is explicitly set.
- Invalid or future-version browser chat state must fail closed to an empty validated state.
- Runtime session identity and client display identity must remain separate across Rust, Python, and frontend boundaries.

## Release Decision

A reviewer may mark a release ready only when all required CI gates are green, both live contracts have fresh artifacts, the latency sample minimum is met in the target environment, and no unresolved high/critical dependency advisory remains. Any exception requires an owner, expiry date, rollback plan, and written risk acceptance.

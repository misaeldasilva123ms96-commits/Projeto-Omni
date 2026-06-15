# Omni CI Repair Planner — Architecture

## Overview

Phase 32 produces metadata repair plans from Phase 31 CI repair loop gate
evidence. It is the bridge between CI failure detection and future
automated patch proposal — it plans *what* to fix without fixing anything.

## Flow

```
Phase 30 CI Monitor  ──►  Phase 31 CI Repair Loop Gate  ──►  Phase 32 CI Repair Planner
                                                                │
                                                                ├─ disabled / dry_run / blocked / plan_repair
                                                                │
                                                                ├─ classify failure categories
                                                                ├─ enforce attempt budget
                                                                ├─ detect secrets in check names
                                                                ├─ build repair plan steps + validation commands
                                                                └─ route next_allowed_phase:
                                                                     plan_ready  → scoped_ci_patch_proposal_gate
                                                                     CI passed   → merge_gate
                                                                     CI pending  → wait_for_ci
                                                                     blocked     → human_review
```

## Source Files

| File | Purpose |
|---|---|
| `ci_repair_planner_types.py` | `CIRepairPlannerRequest` / `CIRepairPlannerResult` dataclasses |
| `ci_repair_planner_truth.py` | `CIRepairPlannerEvidence` + builder + governance decision mapping |
| `ci_repair_planner.py` | `evaluate_ci_repair_planner()` entry function (~1400 lines) |

## Modes

- **disabled**: no planning; blocks immediately.
- **dry_run**: validates evidence, sets status dry_run, no plan.
- **plan_repair**: full planning if evidence passes all checks.
- **blocked**: blocks planning (e.g. secrets detected).

## Failure Categories

Allowed: `test_failure`, `typecheck_failure`, `lint_failure`,
`format_failure`, `build_failure`.

Blocked: `security_failure`, `secret_failure`, `deployment_failure`,
`billing_failure`, `permission_failure`, `unknown_infrastructure_failure`.

## Attempt Budget

- Default max 3 (range 1–10).
- Counted from Phase 31 gate `repair_attempts` count + current planning.
- Exceeding budget sets status to `blocked`.

## Redaction

Secrets (sk-, API_KEY, SECRET, TOKEN, JWT, ghp_, github_pat_) in failing
check names are redacted to `<REDACTED>`.

## Safety

- Requires safe Phase 31 gate result.
- Requires Phase 30 CI monitor evidence.
- Validates PR number, repo, branch, and SHA match expectations.
- Blocks on any Phase 31 unsafe flag (loop started, logs downloaded, etc.).
- All action flags false.
- No subprocess, shell, eval, exec, gh, or provider calls.

# CI Repair Loop Gate

Phase 31 of the Omni Governed Knowledge Sandbox.

## Purpose

The CI Repair Loop Gate decides whether a failed or inconclusive CI monitor
result (from Phase 30) is eligible for a future repair loop. It produces
eligibility metadata, repair plan metadata, and Runtime Truth only.

## Scope

This phase does **not**:

- Start repair loops.
- Download logs.
- Retry or trigger workflows.
- Call providers or agents.
- Create patch proposals.
- Apply patches.
- Edit files.
- Execute commands.
- Mutate Git.
- Commit, push, update PRs, merge, or auto-merge.

This phase **does**:

- Validate Phase 30 CI monitor evidence.
- Validate Phase 29 CI monitor gate evidence (when provided).
- Classify CI failure categories (safe vs. blocked).
- Enforce repair attempt budgets.
- Decide whether a future repair planner phase should proceed.
- Generate structured Runtime Truth evidence.

## Modes

| Mode | Behavior |
|------|----------|
| `disabled` | Blocks all repair-loop eligibility. |
| `dry_run` | Validates evidence but does not mark eligible. |
| `evaluate_repair` | Evaluates eligibility for a future repair loop. |
| `blocked` | Blocks all repair-loop eligibility. |

## Failure Categories

### Allowed (safe to plan repair)

- `test_failure`
- `typecheck_failure`
- `lint_failure`
- `format_failure`
- `build_failure`

### Blocked (requires human intervention)

- `security_failure`
- `secret_failure`
- `deployment_failure`
- `billing_failure`
- `permission_failure`
- `unknown_infrastructure_failure`

## Repair Attempt Budget

- Default max: 3 attempts.
- If `current_repair_attempt >= max_repair_attempts`, eligibility is denied.
- Budget must be between 1 and 10.

## Routing

| CI State | Next Phase |
|----------|------------|
| Failed (safe categories) | `ci_repair_planner` (Phase 32) |
| Pending | `wait_for_ci` |
| Passed | `merge_gate` |
| Blocked / human required | `human_review` |

## Dependencies

- Phase 30: Controlled CI Monitor (required for actual eligibility).
- Phase 29: CI Monitor Gate (optional but supports eligibility).
- Phase 28: Controlled PR Creator (optional evidence).
- Phase 27: PR Creation Gate (optional evidence).

## Public Demo

The public demo must **not** enable unrestricted CI repair automation. This
gate enforces safety checks before any repair loop can begin.

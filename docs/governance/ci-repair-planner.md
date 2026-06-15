# CI Repair Planner — Phase 32

## Purpose

Create a structured repair plan from safe CI failure metadata (Phase 31
repair-loop gate evidence). Planning only — no execution, file edits,
patches, or Git mutation.

## Behavior

- **disabled** (default): no planning.
- **dry\_run**: validate evidence, produce no plan.
- **plan\_repair**: create repair plan metadata + steps + validation commands.
- **blocked**: block all planning.

## Input

Requires clean Phase 31 `ci_repair_loop_gate_result`. Validates Phase 30
CI monitor evidence and Phase 29 gate evidence when provided.

## Output

- `planned` / `blocked` / `dry_run` status
- `repair_plan` (JSON metadata)
- `repair_plan_steps` (step metadata per failure)
- `affected_areas` (safe classification)
- `suggested_validation_commands` (metadata only)
- `runtime_truth` with governance decision

## Restrictions

- All `can_*` action flags are **false**.
- `requires_patch_proposal_gate_phase` true when plan is ready.
- No subprocess, shell, eval, exec, gh, provider, agent, or MCP calls.
- No file writes, patches, commits, pushes, PR updates, or merges.

## Governance Decisions

- `ci_repair_plan_created` — ready for future patch proposal gate.
- `blocked` — secret detected or mode disabled/blocked.
- `dry_run` — evidence validated, no plan created.
- `requires_human_intervention` — blocked categories or missing checks.
- `repair_budget_exceeded` — attempt budget exhausted.
- `repair_not_needed` — CI passed.
- `repair_wait_for_ci` — CI is pending.

# Scoped CI Patch Proposal Gate — Phase 33

## Purpose

Decides whether a safe Phase 32 CI repair plan is eligible for a future
scoped CI patch proposal phase. Gate only — no patch proposals, no hunk
generation, no patch application, no file editing.

## Behavior

- **disabled** (default): no eligibility decision.
- **dry_run**: validate Phase 32 evidence, do not mark eligible.
- **evaluate_patch_proposal**: evaluate whether future scoped CI patch
  proposal is eligible based on clean Phase 32 repair plan evidence.
- **blocked**: block all eligibility.

## Input

Requires clean Phase 32 `ci_repair_planner_result`. Validates Phase 31
repair loop gate evidence, Phase 30 CI monitor evidence, and earlier
phase evidence when provided.

## Output

- `patch_proposal_eligible` / `blocked` / `dry_run` status
- `scoped_patch_proposal_plan` (JSON metadata)
- Validated repair steps, target areas, validation commands
- Scope limits enforced
- Attempt budget enforced

## Restrictions

- All `can_*` action flags are **false**.
- No patch proposal, hunk generation, patch application, file writes.
- No source inspection for edits, code editing.
- No subprocess, shell, eval, exec, gh, provider, agent, MCP calls.
- No log downloads, workflow retry/trigger.
- No Git mutation, commits, pushes, PR updates, merges, auto-merge.

## Governance Decisions

- `scoped_ci_patch_proposal_eligible` — ready for future patch proposal.
- `blocked` — secret detected or mode disabled/blocked.
- `dry_run` — evidence validated, no eligibility marked.
- `requires_human_intervention` — blocked categories or unsafe areas.
- `patch_proposal_not_needed_ci_passed` — CI passed.
- `patch_proposal_wait_for_ci` — CI is pending.
- `patch_proposal_not_eligible_missing_repair_plan` — plan not ready.

## Validated Items

- Repair plan steps (allowed/proposed/inspect/human step types)
- Candidate target areas and file roots
- Suggested validation commands (metadata only)
- Failure categories (allowed vs blocked)
- Scope limits (max files/hunks per file)
- Repair attempt budget

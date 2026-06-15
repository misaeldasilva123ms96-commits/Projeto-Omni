# Scoped CI Patch Proposal Engine — Phase 34

## Purpose

Converts clean Phase 33 gate eligibility and Phase 32 repair plan metadata into
bounded scoped CI patch proposal metadata. Proposal metadata only — no patches
applied, no files written, no code edited, no source inspected, no commands
executed, no Git mutations, no provider/agent/MCP calls.

## Behavior

- **disabled** (default): no proposal evaluation.
- **dry_run**: validate evidence, generate proposal preview, do not mark created.
- **propose_patch**: generate scoped CI patch proposal metadata if all conditions pass.
- **blocked**: block all proposal generation.

## Input

Requires clean Phase 33 `scoped_ci_patch_proposal_gate_result`. Validates
Phase 32 repair planner evidence, Phase 31 repair loop gate, Phase 30 CI monitor,
and earlier phases when provided.

## Output

- `proposal_created` / `blocked` / `dry_run` / `partial` status
- `scoped_ci_patch_proposals` (list of proposal metadata objects)
- `proposal_hunks` (list of hunk metadata objects)
- Validated repair steps, target areas, validation commands
- Scope limits and attempt budget enforced
- Follow-up tests suggested based on failure categories and target areas

## Restrictions

- All `can_*` action flags are **false** (patch, write, inspect, download,
  retry, trigger, call, commit, push, update PR, merge, auto-merge,
  Git mutation, command execution).
- No patch application, file writes, source inspection.
- No subprocess, shell, eval, exec, gh, provider, agent, MCP calls.
- No log downloads, workflow retry/trigger.
- No Git mutation, commits, pushes, PR updates, merges, auto-merge.

## Governance Decisions

- `scoped_ci_patch_proposal_created` — full proposal metadata generated.
- `partial_scoped_ci_patch_proposal_created` — partial proposal (some steps skipped).
- `blocked` — secret detected or mode disabled/blocked.
- `dry_run` — evidence validated, no proposal created.
- `requires_human_intervention` — blocked categories or unsafe areas.
- `proposal_not_needed_ci_passed` — CI passed.
- `proposal_wait_for_ci` — CI is pending.
- `proposal_not_created_missing_repair_plan` — plan not ready.
- `proposal_not_created_gate_ineligible` — gate not eligible.

## Validated Items

- Repair plan steps (validated against gate unsafe types and credential patterns)
- Candidate target areas and file roots (allowed vs blocked)
- Suggested validation commands (safe vs blocked patterns)
- Failure categories (operation mapping)
- Scope limits (max files/hunks per file)
- Repair attempt budget
- Secrets detection (credential patterns redacted)

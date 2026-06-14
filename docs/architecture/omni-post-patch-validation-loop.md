# Omni Post-Patch Validation Loop Architecture

Phase 22 validates the output of the Controlled Branch Patch Applier.

```text
Phase 21 patch apply evidence
  -> Phase 22 post-patch validator
  -> Phase 18 autonomous test runner loop
  -> Phase 17 sandbox command runner
  -> Phase 16 command execution gate
```

The validator does not call the command runner or command gate directly. It delegates validation execution to Phase 18 only.

## Responsibilities

The Post-Patch Validation Loop:

- Accepts Phase 21 patch application results.
- Checks patch Runtime Truth for unsafe conditions.
- Filters validation commands to safe families.
- Enforces non-main branch metadata.
- Calls the Phase 18 loop for validation execution.
- Classifies validation results.
- Links patch application and validation evidence.
- Emits Runtime Truth.
- Recommends the next governed action.

## Non-Responsibilities

The validator does not edit files, apply patches, write files, run commands directly, mutate Git, commit, push, open pull requests, merge, rebase, call providers, use MCP, call agents, access secrets, or write Vault entries.

## Classifications

Validation classifications include:

- `validation_passed`
- `tests_failed`
- `build_failed`
- `lint_failed`
- `typecheck_failed`
- `format_failed`
- `command_blocked`
- `command_timed_out`
- `unsafe_command`
- `secret_detected`
- `invalid_patch_apply_evidence`
- `protected_file_modified`
- `git_mutation_detected`
- `main_modification_detected`
- `unknown_failure`

## Recommended Actions

Recommended next actions include:

- `ready_for_commit_phase`
- `run_additional_validations`
- `start_repair_cycle`
- `escalate_to_human`
- `blocked_by_policy`
- `no_action_needed`
- `wait_for_manual_review`

`ready_for_commit_phase` is metadata only. Commit automation belongs to a later phase.

## Runtime Truth Linkage

Runtime Truth includes child evidence from Phase 21 and Phase 18 so later governance can trace the patch from application to validation.

This phase marks code editing, patch application, file writing, Git mutation, PR creation, PR merge, provider calls, agent calls, MCP use, Vault writing, and main modification false.

Phase 23 consumes this evidence to produce a controlled commit eligibility decision. The decision is metadata only; commit execution remains outside Phase 22 and Phase 23.

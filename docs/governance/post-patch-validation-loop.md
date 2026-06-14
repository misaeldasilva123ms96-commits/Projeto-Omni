# Post-Patch Validation Loop Governance

Phase 22 adds the Post-Patch Validation Loop for Projeto Omni.

It validates applied patches by sending allowed validation commands through the Phase 18 Autonomous Test Runner Loop. It does not execute commands directly, edit files, apply patches, mutate Git, commit, push, open pull requests, merge, rebase, call providers, use MCP, call agents, use network access, or write to the Vault.

## Governance Boundary

The validator links Phase 21 patch application evidence with Phase 18 validation evidence.

It may recommend `ready_for_commit_phase` as metadata only. It never stages files, commits, pushes, opens a pull request, or merges.

All mutation capabilities remain disabled:

- `can_commit = false`
- `can_push = false`
- `can_open_pr = false`
- `can_merge = false`
- `can_edit_code = false`
- `can_apply_patch = false`
- `can_mutate_git = false`
- `can_call_provider = false`
- `can_call_agent = false`
- `can_use_network = false`

## Modes

- `disabled`: default. Blocks validation.
- `dry_run`: checks patch evidence and planned commands without running validations.
- `validate_patch`: delegates allowed validations to Phase 18.
- `blocked`: blocks all validation.

Unknown modes are blocked.

## Patch Evidence Requirements

Validation may proceed only when Phase 21 evidence shows a successful applied patch, Runtime Truth exists, no secrets were detected, Git was not mutated, main was not modified, commands were not executed by Phase 21, and protected files were not modified.

Protected file evidence escalates to humans. This includes `.env`, `.git`, ADR, governance, security, CI, production, deploy, billing, credential, and private-key scopes.

## Validation Commands

Allowed validation commands include Python, npm, Cargo, `git diff --check`, JSON validation, compile checks, and version commands already compatible with the governed command gates.

Blocked commands include Git mutation, GitHub CLI, network, deploy, destructive, and secret-reading commands.

The validator never runs commands itself. It passes commands to Phase 18, which remains responsible for using the Phase 17 runner and Phase 16 execution gate.

## Runtime Truth

Every request emits Runtime Truth with event type `sandbox.post_patch_validation.loop`.

Evidence records patch application source evidence, validation commands, command counts, validation result, classification, recommended next action, commit-readiness metadata, child Runtime Truth events, and locked mutation flags.

## Human Escalation

Secrets, protected files, Git mutation evidence, main modification evidence, invalid patch evidence, unsafe commands, and blocked commands require human intervention.

Public demos must not expose unrestricted validation loops or commit controls.

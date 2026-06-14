# Controlled Commit Executor Governance

Phase 24 adds the Controlled Commit Executor for the Omni Governed Knowledge Sandbox.

This is the first real commit layer. It may create one Git commit only when Phase 23 Controlled Commit Gate evidence is clean and the workspace is on a verified non-main branch.

## Required Evidence

The executor requires Phase 23 commit gate output showing:

- `commit_eligible: true`
- `commit_ready_metadata_only: true`
- `success: true`
- `blocked: false`
- `validation_passed: true`
- `patch_was_applied: true`
- clean Runtime Truth

If the gate reports secrets, main modification, unsafe Git mutation evidence, PR creation, PR merge, blocked status, or human intervention, the executor blocks.

## Allowed Git Operations

The executor may use only fixed Git argv operations with `shell=False`:

- `git status --short`
- `git diff --name-only`
- `git add -- <safe files>`
- `git commit -m <safe message>`
- `git rev-parse --abbrev-ref HEAD`
- `git rev-parse HEAD`

It never runs arbitrary command text and never uses user supplied Git subcommands.

## Prohibited Operations

The executor does not push, open PRs, merge, rebase, create branches, checkout or switch branches, edit files, apply patches, run tests, call providers, call MCP, call agents, use network access, or write to the Vault.

It never stages `.`, `-A`, `--all`, protected files, unrelated files, `.env`, secrets, governance/security/ADR/CI/deploy/billing files, lockfiles, `.git/**`, absolute paths outside the repository, or path traversal.

## Branch Safety

Actual commit execution is blocked unless:

- `current_branch` is provided
- `git rev-parse --abbrev-ref HEAD` verifies the same branch
- the branch is not `main`
- the branch is not the base branch
- `target_branch` is not `main`
- `base_branch` is `main`
- the branch is not a release or production branch

The executor never changes branches.

## Commit Message Safety

The final commit message is selected from safe Phase 23 metadata, request metadata, or a conservative fallback. Secret-like content is redacted and blocks the commit.

## Runtime Truth

Every attempt emits Runtime Truth with event type `sandbox.commit_executor.commit`.

Successful commits record pre-commit head, post-commit head, commit SHA, attempted Git operations, completed Git operations, staged files, and governance decision.

The Runtime Truth keeps `pushed`, `pr_created`, `pr_merged`, `branch_created`, `checkout_performed`, `rebase_performed`, `merge_performed`, `network_used`, `provider_called`, `agent_called`, `mcp_used`, `vault_written`, and `main_modified` false.

Public demos must not enable unrestricted commit automation.

Phase 25 consumes clean commit executor evidence to decide whether a future push phase may proceed. The push decision is metadata only and does not contact remotes or run `git push`.

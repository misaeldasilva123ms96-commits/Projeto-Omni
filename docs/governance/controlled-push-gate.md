# Controlled Push Gate Governance

Phase 25 adds the Controlled Push Gate for the Omni Governed Knowledge Sandbox.

The gate decides whether a committed non-main branch is eligible for a future push phase. It produces push eligibility metadata, a structured push plan, required pre-push checks, and Runtime Truth.

## Non-Execution Rule

This phase does not execute `git push`, contact remotes, execute commands, mutate Git, stage files, commit, push to main, force push, open PRs, merge, rebase, create branches, checkout or switch branches, edit files, apply patches, call providers, call MCP, call agents, use network access, or write to the Vault.

The following capability flags remain false:

- `can_execute_push`
- `can_force_push`
- `can_push_main`
- `can_open_pr`
- `can_merge`
- `can_rebase`
- `can_create_branch`
- `can_checkout`
- `can_edit_code`
- `can_apply_patch`

## Required Evidence

Push eligibility requires clean Phase 24 commit executor evidence. If Phase 23 commit gate evidence is supplied, it must also be clean.

The gate blocks when evidence is missing, the commit was not created, the commit SHA is missing, Runtime Truth is missing when required, or source evidence reports push, PR, merge, rebase, checkout, branch creation, main modification, network, provider, MCP, agent, Vault, or secret activity.

## Branch and Remote Governance

The gate blocks:

- `main` as current, target, remote, or push ref
- release, production, or protected branches
- force-like refs
- refspec mutation
- credential-like remote metadata
- missing or unsafe remote names
- remote branches that do not match the current branch

No Git command is run to discover branch or remote state. All decisions use supplied metadata only.

## File Governance

Committed file metadata may include:

- `backend/python/**`
- `backend/rust/**`
- `frontend/**`
- `tests/**`
- `docs/**`
- `sandbox/local/**`
- `vault/templates/**`

Protected files, `.env`, secrets, credentials, ADR, governance, security, CI, deploy, billing, lockfiles, `.git/**`, absolute paths outside the repository, and path traversal require blocking or human intervention.

## Runtime Truth

Every request emits Runtime Truth with event type `sandbox.push_gate.decision`.

Runtime Truth records push eligibility, commit evidence linkage, branch safety, remote safety, protected branch detection, force push detection, main push detection, file scope, governance decision, and locked mutation flags.

`push_executed`, `force_push_executed`, `main_pushed`, `command_executed`, `git_mutated`, `commit_executed`, `files_staged`, `code_edited`, `patch_applied`, `files_written`, `pr_created`, `pr_merged`, `branch_created`, `checkout_performed`, `rebase_performed`, `merge_performed`, `network_used`, `provider_called`, `agent_called`, `mcp_used`, `vault_written`, and `main_modified` remain false in Phase 25.

Public demos must not enable unrestricted push automation.

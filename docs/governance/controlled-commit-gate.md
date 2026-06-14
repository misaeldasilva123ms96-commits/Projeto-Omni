# Controlled Commit Gate Governance

Phase 23 adds the Controlled Commit Gate for the Omni Governed Knowledge Sandbox.

The gate decides whether a validated patch is eligible for a future commit phase. It produces commit eligibility metadata, a structured commit plan, a safe proposed commit message, and Runtime Truth evidence.

## Non-Execution Rule

This phase does not stage files, commit, push, open pull requests, merge, rebase, execute commands, edit files, apply patches, call providers, call MCP, call agents, use network access, or write to the Vault.

The following capability flags remain false:

- `can_execute_commit`
- `can_stage_files`
- `can_push`
- `can_open_pr`
- `can_merge`
- `can_edit_code`
- `can_apply_patch`
- `can_mutate_git`
- `can_call_provider`
- `can_call_agent`
- `can_use_network`

## Required Evidence

Commit eligibility requires clean evidence from:

- Phase 21 Controlled Branch Patch Applier
- Phase 22 Post-Patch Validation Loop

The gate blocks when patch evidence is missing, validation evidence is missing, validation failed, validation timed out, Runtime Truth is missing when required, or any source evidence reports mutation that earlier phases were not allowed to perform.

## Branch Governance

The gate blocks commit eligibility when:

- `current_branch` is missing while non-main branch metadata is required
- `current_branch` is `main`
- `current_branch` equals `base_branch`
- `target_branch` is `main`
- `base_branch` is not `main`
- the branch looks like a protected release or production branch
- metadata indicates direct main editing

The gate never runs Git commands to discover branch state. Branch metadata must be supplied by the caller.

## File Governance

Allowed file metadata may include:

- `backend/python/**`
- `backend/rust/**`
- `frontend/**`
- `tests/**`
- `docs/**`
- `sandbox/local/**`
- `vault/templates/**`

Protected files and paths require blocking or human intervention:

- `.env` and `.env.*`
- secret, credential, token, and private key files
- `vault/08_ADR/**`
- `docs/governance/**`
- `docs/security/**`
- `.github/workflows/**`
- `.circleci/**`
- production deploy files
- billing files
- lockfiles
- `.git/**`
- absolute paths outside the repository
- path traversal

## Commit Plan Metadata

The gate may produce:

- commit type
- commit scope
- eligible file list
- proposed commit message
- required pre-commit checks
- validation evidence summary

The proposed commit message is metadata only. It must not contain secrets or raw file contents.

## Runtime Truth

Every evaluation emits Runtime Truth with event type `sandbox.commit_gate.decision`.

Runtime Truth records eligibility, source evidence linkage, file counts, validation status, protected file detection, secret detection, Git/main mutation detection, governance decision, and locked mutation flags.

`commit_executed`, `files_staged`, `command_executed`, `code_edited`, `patch_applied`, `files_written`, `git_mutated`, `pr_created`, `pr_merged`, `network_used`, `provider_called`, `agent_called`, `mcp_used`, `vault_written`, and `main_modified` remain false in Phase 23.

## Human Intervention

Human intervention is required for protected files, secrets, missing or unsafe evidence, failed validation, timed-out validation, Git mutation evidence, main modification evidence, PR creation evidence, PR merge evidence, network/provider/MCP/Vault activity, unsafe branches, and direct-main-edit metadata.

Public demos must not enable unrestricted commit automation.

# Controlled Branch Patch Applier Governance

Phase 21 adds the Controlled Branch Patch Applier for the Omni Governed Knowledge Sandbox.

This is the first real code and file modification layer. It is denied by default and applies only validated, scoped patch proposals when every governance gate passes.

## Hard Boundaries

The applier does not mutate Git. It does not commit, push, open pull requests, merge, rebase, run tests, execute commands, call providers, call agents, use MCP, or write to the Vault.

The applier never discovers the branch by itself. The current branch, target branch, base branch, and workspace root must be supplied as request metadata.

## Modes

- `disabled`: default. Blocks patch application.
- `dry_run`: validates proposals and reports what would be applied without writing files.
- `apply_to_branch`: writes safe scoped files inside the explicit workspace root when branch and file gates pass.
- `blocked`: blocks all application.

Unknown modes are blocked.

## Required Gates

Actual application requires:

- Explicit `workspace_root`.
- `base_branch = main`.
- `current_branch` supplied and not `main`.
- `current_branch` different from `base_branch`.
- `target_branch` not `main`.
- Safe relative file paths inside `workspace_root`.
- Supported operations only.
- Explicit snippet hunks.
- Unique `before_context` for `modify_existing`.
- Safe validation commands as metadata.

## Protected Files

The applier blocks:

- `.env` and secret-bearing files.
- `.git/**`.
- ADR files.
- Governance documents.
- Security documents.
- CI workflow files.
- Production, deploy, billing, credential, private-key, and lockfile changes.
- Path traversal and absolute paths outside the workspace.

## Supported Operations

Supported operations:

- `modify_existing`
- `add_test`
- `add_documentation`

File creation is blocked unless `allow_file_create` is true. Delete, rename, move, chmod, dependency, CI, governance, security, production, billing, and secret changes are not supported.

## Runtime Truth

Every attempt emits Runtime Truth with event type `sandbox.patch_applier.apply`.

Evidence records the mode, branch metadata, workspace metadata, requested files, considered files, applied files, blocked files, hunk counts, pre/post hash counts, and governance decision.

When files are actually written, Runtime Truth marks `files_written`, `code_edited`, and `patch_applied` true. It always keeps command execution, Git mutation, PR creation, PR merge, network use, provider call, agent call, MCP use, Vault writing, and main modification false.

## Follow-Up Validation

The applier does not run tests. When a patch is applied, it marks follow-up validation as required and carries safe validation commands as metadata only.

## Public Demo Boundary

Public demo surfaces must not enable unrestricted patch application. Any demo control must remain denied by default and scoped to explicit, non-main, test-safe workspaces.

Phase 22 consumes patch application evidence from this phase and validates it through the Phase 18 Autonomous Test Runner Loop.

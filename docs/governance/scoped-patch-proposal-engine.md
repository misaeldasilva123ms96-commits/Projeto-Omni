# Scoped Patch Proposal Engine Governance

Phase 20 adds the Scoped Patch Proposal Engine for the Omni Governed Knowledge Sandbox.

The engine transforms a Phase 19 repair plan into structured patch proposal metadata. It does not apply patches, edit code, write files, execute commands, mutate Git, create branches, create commits, push, open pull requests, merge, call providers, call agents, use MCP, or write to the Vault.

## Governance Boundary

The engine is a planning boundary only. It may describe future changes, but it cannot make those changes.

All proposal outputs keep these capabilities disabled:

- `can_apply_patch = false`
- `can_edit_code = false`
- `can_write_files = false`
- `can_mutate_git = false`
- `can_execute_commands = false`
- `can_call_provider = false`
- `can_call_agent = false`
- `can_use_network = false`
- `can_open_pr = false`
- `can_merge = false`

Any future patch application requires a separate governed phase with Runtime Truth, sandbox gating, scoped approval, and human-defined boundaries.

## Modes

- `disabled`: default mode; no proposal generation.
- `dry_run`: classifies the repair plan and reports what would be proposed.
- `proposal_only`: creates in-memory patch proposal metadata.
- `blocked`: blocks all proposal generation.

Unknown modes are blocked.

## Inputs

The engine may consume Phase 19 repair plan metadata, direct repair category, failure classification, suspected files, allowed files, blocked files, proposed repair steps, validation commands, and optional file contexts explicitly provided in the request.

The engine must not read repository files to build proposals. If file contexts are not supplied, hunks are intent-only.

## Patch Proposal Output

Each proposal includes proposal id, file path metadata, operation, target area, summary, rationale, proposed change type, hunk metadata, risk level, human-review requirement, future patch-apply eligibility, validation command metadata, and notes.

Hunks are metadata only. Proposed snippets are allowed only when the caller explicitly provides safe file context. Snippets are never applied.

## Allowed Operations

The proposal engine may describe these operations as metadata:

- `modify_existing`
- `add_test`
- `add_documentation`
- `no_change_needed`

## Blocked Or Escalated Operations

The following operations are blocked or require human intervention:

- Delete, rename, or move files.
- Permission changes.
- Dependency upgrades.
- CI threshold changes.
- Security policy changes.
- Governance policy changes.
- Production deployment changes.
- Billing changes.
- Secret changes.

## File Scope

Allowed metadata scopes:

- `backend/python/**`
- `backend/rust/**`
- `frontend/**`
- `tests/**`
- `docs/**`
- `sandbox/local/**`
- `vault/templates/**`

High-risk scopes require human intervention: ADR files, governance documents, security documents, CI workflow files, and production, deploy, billing, secret, credential, or private-key paths.

Blocked scopes include path traversal, repository internals, absolute paths outside the repository, and secret-bearing files.

## Validation Commands

Validation commands are metadata only. They must be safe command families compatible with the governed command gates.

Git mutation, GitHub CLI, network, provider, deploy, destructive, and secret-reading commands are not valid validation metadata.

## Secret Handling

Secret-like content is conservatively redacted and blocked. Detection covers markers such as API key names, token labels, bearer authorization text, private-key labels, and environment-file references.

When secret-like content is detected, the proposal is blocked, human intervention is required, risk becomes critical, and Runtime Truth records the governance outcome without exposing the secret-like value.

## Runtime Truth

Every request produces Runtime Truth evidence with event type `sandbox.patch_proposal.plan`.

Runtime Truth records proposal mode, repair category, failure classification, patch scope, complexity, counts, governance decision, human intervention requirement, and safety flags showing no patch was applied and no mutation occurred.

## Human Intervention

Human intervention is mandatory for security, governance, ADR, production, billing, destructive, secret, policy-blocked, and main-branch patch scopes.

Public demo mode must not enable patch application. It may display proposal metadata only when redaction and governance checks pass.

Phase 21 may consume proposal metadata from this phase and apply explicit snippets only when workspace, branch, path, operation, hunk, and secret gates all pass.

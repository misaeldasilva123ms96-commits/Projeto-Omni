---
title: Vault and Sandbox Governance Policy
status: draft
owner: omni
created: 2026-06-09
updated: 2026-06-09
tags:
  - governance
  - policy
  - vault
  - sandbox
---

# Vault and Sandbox Governance Policy

## Purpose

This policy defines how Projeto Omni governs knowledge records, sandbox activity, agent roles, and future write capabilities.

## Governance Decision Flow

1. Proposal: a maintainer or agent creates a written proposal in documentation or an ADR.
2. Classification: the proposal is classified as documentation, vault record, runtime change, sandbox change, provider change, or governance change.
3. Risk review: reviewers check secrets, main branch safety, external code risk, and public demo impact.
4. Approval: approved proposals receive a clear status and owner.
5. Branch work: changes happen on a non-main branch.
6. Validation: required checks are run and recorded.
7. Review: human review confirms scope and evidence.
8. Merge by approved process: no direct push or merge to `main`.

## Main Branch Rule

Direct push or merge to `main` is explicitly blocked. All changes must be made on a branch, reviewed, and integrated only through the approved project process.

## Documentation-Only Phase Rule

During this phase, contributors may create or edit Markdown documentation and `.gitkeep` placeholders only. They must not add runtime code, MCP integration, sandbox execution code, provider calls, real credentials, or copied external code.

## Vault Storage Policy

The vault may store:

- Governance notes.
- ADRs.
- Runtime evidence summaries.
- Architecture records.
- Agent prompt templates.
- Incident records.
- Provider evaluations.
- Sandbox reports.

The vault must not store:

- Real secrets, API keys, tokens, passwords, private keys, or credentials.
- `.env` values.
- Unredacted sensitive logs.
- Unapproved personal or customer data.
- Runtime implementation code during this phase.
- Copied code from external projects.

## Frontmatter Policy

Substantive records should include frontmatter with:

- `title`
- `status`
- `owner`
- `created`
- `updated`
- `tags`

Records should move from `draft` to `review` to `approved` only through the governance decision flow.

## Runtime Truth Evidence Policy

Runtime Truth records must be evidence-backed. They must identify what was observed, where it was observed, when it was observed, and who reviewed it.

Runtime Truth records must separate:

- Fact: directly observed evidence.
- Interpretation: reasoned conclusion from evidence.
- Decision: approved action based on evidence.

## MCP Read-Only First Policy

Future MCP access must start read-only. Write tools, command execution, provider mutation, and filesystem mutation are blocked until a separate governed write policy is approved and implemented.

## Future Governed Write Policy

Future governed writes require:

- Approved use case.
- Approved target paths.
- Branch-only write behavior.
- Audit logs.
- Human review before merge.
- Secret scanning.
- Rollback plan.

No governed write policy may authorize direct push or merge to `main`.

## Agent Role Policy

Hermes coordinates context and routing.

Aider supports implementation when implementation is approved.

Codex supports repository analysis, documentation, validation, and approved implementation.

Omni owns the governing knowledge model and ensures consistency between policy, docs, vault records, and evidence.

Agents must follow the same branch, secret, and review policies as humans.

## Public Demo Policy

Public demos must be sanitized, must not expose sensitive data, and must not imply that unimplemented sandbox enforcement exists.

Allowed:

- Mock data.
- Redacted examples.
- Documentation walkthroughs.
- Governance flow demonstrations.

Blocked:

- Real credentials.
- Private operational logs.
- Customer confidential data.
- Direct write demonstrations against `main`.
- Unapproved provider account access.

## Testing Checklist

- Current branch is not `main`.
- Changes are limited to approved docs and vault structure.
- `git status --short` has been reviewed.
- `git diff --check` passes.
- No runtime code changed.
- No secrets were added.
- No direct push or merge to `main` occurred.

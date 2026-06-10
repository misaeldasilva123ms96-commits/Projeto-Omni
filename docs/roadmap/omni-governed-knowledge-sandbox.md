---
title: Omni Governed Knowledge Sandbox Roadmap
status: draft
owner: omni
created: 2026-06-09
updated: 2026-06-09
tags:
  - roadmap
  - governance
  - sandbox
---

# Omni Governed Knowledge Sandbox Roadmap

## Purpose

The Omni Governed Knowledge Sandbox initiative creates a controlled knowledge and experimentation layer for Projeto Omni. It separates long-lived architecture records, governance decisions, runtime evidence, and agent prompts from executable runtime code.

This phase starts with documentation and a safe vault structure only. It does not add runtime code, MCP integration, sandbox execution, credentials, or external project code.

## Outcomes

- Define the purpose and boundaries of the Omni Knowledge Vault.
- Define the purpose and boundaries of the Omni Governed Sandbox.
- Establish safe Markdown and frontmatter conventions.
- Establish evidence rules for Runtime Truth records.
- Establish read-only-first MCP policy and future governed write policy.
- Document agent roles for Hermes, Aider, Codex, and Omni.
- Document public demo restrictions and testing expectations.

## Phases

### Phase 0: Documentation and Vault Structure

Status: active.

Scope:

- Create `docs/` architecture, governance, security, and roadmap documents.
- Create `vault/` folders, index, and templates.
- Define safe storage, secret handling, and main branch protection rules.

Out of scope:

- Runtime code.
- MCP integration.
- Sandbox execution.
- Provider API calls.
- Real secrets, API keys, tokens, `.env` values, or credentials.
- External project code.

### Phase 1: Governance Review

Status: planned.

Scope:

- Review policies with project maintainers.
- Convert accepted decisions into ADRs.
- Identify required approvals for any future sandbox execution.

### Phase 2: Read-Only Knowledge Access

Status: planned.

Scope:

- Define read-only retrieval rules for approved vault and docs content.
- Define audit records for reads.
- Keep all writes manual or pull-request based until governed writes are approved.

### Phase 3: Governed Sandbox Design

Status: planned.

Scope:

- Specify command categories, isolation boundaries, audit logs, and review gates.
- Define how sandbox reports are produced and reviewed.
- Keep execution disabled until explicitly approved in a later implementation task.

### Phase 4: Governed Writes

Status: planned.

Scope:

- Define proposal, approval, execution, and review flow for controlled writes.
- Require branch-based changes and human review.
- Preserve the explicit rule: no direct push or merge to `main`.

## Non-Negotiable Rules

- Do not modify `main` directly.
- Do not push directly to `main`.
- Do not merge directly to `main`.
- Do not store real secrets or credentials.
- Do not add runtime code in this phase.
- Do not add MCP integration in this phase.
- Do not add sandbox execution code in this phase.
- Do not copy code from external projects.

## Testing Checklist

- Confirm the current branch is not `main`.
- Confirm created files are Markdown or `.gitkeep` placeholders only.
- Run `git status --short`.
- Run `git diff --check`.
- Confirm no runtime code changed.
- Confirm no real secrets, API keys, tokens, `.env` values, or credentials were added.

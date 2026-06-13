---
title: Omni Governed Sandbox
status: draft
owner: omni
created: 2026-06-09
updated: 2026-06-09
tags:
  - architecture
  - sandbox
  - governance
---

# Omni Governed Sandbox

## Purpose

The Omni Governed Sandbox is a future controlled execution environment for research, validation, and agent-assisted analysis. Its purpose is to let agents and maintainers test ideas under clear command restrictions, audit trails, and review gates.

This document defines architecture intent only. It does not implement sandbox execution code.

## Sandbox Principles

- Read-only first.
- Least privilege.
- Explicit approval for writes.
- No secret exposure.
- Full auditability.
- Branch-based changes only.
- No direct push or merge to `main`.

## Allowed Command Categories

Allowed categories for a future governed sandbox may include:

- Read-only file inspection, such as listing files or reading approved text files.
- Git inspection, such as branch checks, status checks, and diffs.
- Static validation, such as Markdown checks and formatting checks.
- Dependency inventory commands that do not install, update, or execute package scripts.
- Test commands approved by policy and scoped to the current branch.
- Documentation generation that writes only to approved documentation paths after governance approval.

## Blocked Command Categories

Blocked by default:

- Commands that expose secrets, tokens, credentials, private keys, or `.env` values.
- Direct pushes or merges to `main`.
- Destructive filesystem commands.
- Network exfiltration commands.
- Unapproved package installation or dependency updates.
- Commands that execute downloaded code.
- Production deployment commands.
- Cloud account mutation commands.
- Credential manager access.
- Sandbox escape attempts.
- Any command intended to bypass review or governance.

## Secret Handling

The sandbox must treat secrets as unavailable. It must not request, print, store, infer, or transform real secrets.

Acceptable secret references:

- Placeholder names such as `OMNI_PROVIDER_API_KEY`.
- Documentation that says where a secret would be configured without including its value.
- Redacted examples such as `[REDACTED]`.

Blocked secret references:

- Real API keys, tokens, passwords, private keys, session cookies, or recovery codes.
- `.env` file values.
- Screenshots or logs containing unredacted credentials.

## MCP Read-Only First Policy

Any future MCP integration must begin with read-only capabilities only. Read-only access must be scoped, logged, and reviewable.

Read-only MCP access may include:

- Listing approved knowledge records.
- Reading approved documentation.
- Reading approved vault notes.
- Producing summaries with source references.

Read-only MCP access must not:

- Modify files.
- Execute commands.
- Store credentials.
- Call providers with private data without approval.
- Bypass branch governance.

## Future Governed Write Policy

Governed writes require a separate approval process before implementation.

Future write access must include:

- A written proposal.
- Approved scope.
- Branch-only changes.
- Human review.
- Audit trail.
- Rollback plan.
- Explicit exclusion of direct push or merge to `main`.

## Agent Roles

Hermes:

- Coordinates routing, messages, and high-level operating context.
- Should prefer approved knowledge records over ad hoc memory.

Aider:

- Assists with codebase-oriented edits when implementation is approved.
- Must respect branch, review, and no-main rules.

Codex:

- Assists with repository analysis, documentation, validation, and implementation when approved.
- Must not add runtime code during documentation-only phases.

Omni:

- Represents the governed project system and decision framework.
- Owns the consistency between vault knowledge, docs, policies, and runtime truth.

## Phase 10 Agent Workflow Policy

Phase 10 adds policy-only classification for future supervised agent workflows. It does not execute Hermes, Aider, Codex, Claude, Omni, or any external agent.

Agent workflow policy keeps execution, edits, tests, and PR actions as proposal or request records. Direct command execution, direct file edits, provider calls, network calls, MCP writes, vault writes, push to `main`, and merge to `main` remain blocked.

Runtime Truth is required for future supervised actions, and sandbox governance is required before any future execution request can proceed.

## Public Demo Restrictions

Public demos must use sanitized data only.

Public demos must not include:

- Real secrets or credentials.
- Private repository data unless explicitly approved.
- Customer confidential data.
- Unredacted logs.
- Claims of sandbox enforcement before implementation exists.
- Any direct push or merge to `main`.

Public demos may include:

- Documentation structure.
- Mock records.
- Redacted examples.
- Architecture diagrams or narratives.
- Policy walkthroughs.

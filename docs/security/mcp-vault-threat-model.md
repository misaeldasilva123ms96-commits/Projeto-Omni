---
title: MCP Vault Threat Model
status: draft
owner: omni
created: 2026-06-11
updated: 2026-06-11
tags:
  - security
  - vault
  - mcp
  - threat-model
---

# MCP Vault Threat Model

## Scope

This threat model covers Phase 8 MCP vault read-only policy. It does not cover a real MCP server, MCP client, connector, provider context pipeline, or agent automation because those are not implemented in this phase.

## Assets

- Governed vault notes.
- Runtime Truth records.
- Sandbox reports.
- Governance decisions.
- Agent prompt records.
- Future MCP policy decisions.

## Threats

- Enabling MCP access before human approval.
- Treating draft or unreviewed vault notes as trusted context.
- Allowing write, delete, rename, move, or attachment operations through MCP.
- Allowing command execution through MCP operation names.
- Allowing provider or network operations through MCP operation names.
- Leaking secret-like content from vault notes into future context.
- Presenting public demos as if governed MCP integration is already implemented.

## Controls

- MCP vault access is disabled by default.
- Read-only mode only permits `list_notes`, `read_note`, `search_notes`, and `get_frontmatter` policy decisions.
- Write, delete, execute, provider, and network operation names are blocked as critical risk.
- Unknown operations are blocked by default and require approval.
- Future trusted vault context is limited to `approved` and `reviewed` notes.
- Phase 8 policy does not read files, write files, execute commands, call providers, call network APIs, or import MCP SDKs.

## Required Future Review

Before any future MCP adapter is enabled, a human review must approve:

- The exact MCP server or client boundary.
- Read-only enforcement.
- Vault path restrictions.
- Secret handling.
- Runtime Truth evidence.
- Audit logging.
- Public demo restrictions.
- Rollback plan.

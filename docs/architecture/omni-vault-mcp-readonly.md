---
title: Omni Vault MCP Read-Only Policy
status: draft
owner: omni
created: 2026-06-11
updated: 2026-06-11
tags:
  - architecture
  - vault
  - mcp
  - read-only
---

# Omni Vault MCP Read-Only Policy

## Purpose

Phase 8 defines policy and validation rules for future MCP read-only access to the Omni Knowledge Vault.

This phase is policy-only. It does not start a real MCP server, integrate an MCP SDK or client, perform network calls, read vault notes through MCP, write vault notes, call providers, or automate agents.

## Modes

The policy supports three modes:

- `disabled`: default mode. All MCP vault operations are blocked.
- `read_only`: future read-only operations may be classified as allowed when they are explicitly in the read allowlist.
- `write_blocked`: future mode for environments where read policy decisions are permitted while write operations remain blocked.

MCP vault access must remain `disabled` until a separate human-reviewed governance decision enables a later phase.

## Read-Only Operations

The future read-only operation names are plain strings:

- `list_notes`
- `read_note`
- `search_notes`
- `get_frontmatter`

These operations only become policy-allowed in `read_only` or `write_blocked` mode. Phase 8 does not execute them.

## Blocked Operations

The policy blocks mutation, command, provider, and network operation names:

- `write_note`
- `edit_note`
- `delete_note`
- `rename_note`
- `move_note`
- `create_note`
- `update_frontmatter`
- `attach_file`
- `run_command`
- `execute_tool`
- `provider_call`
- `network_fetch`

Unknown operations are blocked by default, marked high risk, and require approval.

## Vault Trust Boundary

Future MCP read-only access may consider only reviewed vault notes trusted:

- `approved`
- `reviewed`

Draft, review, deprecated, archived, unknown, malformed, outside-root, non-Markdown, or secret-like notes must not be treated as trusted context.

## Public Demo Restriction

Public demos must not enable MCP write access. They must not imply that MCP integration exists in Phase 8, because this phase only defines policy decisions for a future adapter.

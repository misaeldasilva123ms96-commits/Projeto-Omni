---
title: Omni Agent Sandbox Workflow
status: draft
owner: omni
created: 2026-06-13
updated: 2026-06-13
tags:
  - architecture
  - sandbox
  - agents
---

# Omni Agent Sandbox Workflow

## Phase 10 Boundary

Phase 10 introduces policy-only classification for future agent workflows. Hermes, Aider, Codex, Claude, and Omni are policy identities in this phase, not connected runtime agents.

No agent is executed. No provider is called. No MCP server or client is integrated. No shell command runs. No file is edited. No pull request is opened by the policy layer.

## Future Flow

Future supervised workflows must follow this shape:

1. A human or approved controller submits an agent workflow request.
2. The policy classifies the agent identity, action, mode, and branch boundary.
3. Blocked actions stop immediately.
4. Allowed actions remain proposal or request records.
5. Runtime Truth evidence is recorded before any later supervised action can proceed.
6. Human approval remains required.

## Branch Boundary

`main` is protected by policy. Push, merge, direct edit, and automatic merge actions targeting `main` are always blocked.

PR open requests may be proposed only from non-main head branches. Base branch may be `main`, but merge remains blocked.

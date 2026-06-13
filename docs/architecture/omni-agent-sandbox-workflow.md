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

## Phase 11 Runtime Truth Contract

Phase 11 adds Runtime Truth evidence generation for agent workflow policy decisions. It records what the policy decided; it does not perform the requested action.

The evidence contract preserves these boundaries:

- Agents are not executed.
- Commands are not executed.
- Providers are not called.
- MCP is not used.
- Vault notes are not written.
- Git state is not mutated.
- Pull requests are not created or merged.

The governance decision is derived from the policy outcome. Blocked decisions stay blocked, allowed decisions that require approval become `requires_approval`, and unsafe or inconsistent evidence is forced to `blocked`.

## Phase 12 Report Rendering

Phase 12 renders Agent Runtime Truth evidence into Markdown report strings in memory. It also returns suggested report metadata, including a filename and suggested vault path.

The suggested vault path is not a file operation. It is only metadata for later human review or a separately governed draft-note proposal.

This phase does not execute agents, execute commands, call providers, use MCP, write vault notes, mutate Git, create pull requests, or merge pull requests.

## Phase 13 Draft Proposals

Phase 13 can validate a rendered agent sandbox report against the governed draft write policy and return an in-memory draft proposal.

The proposal is not a vault note. It does not create files, mutate the vault, execute agents, execute commands, call providers, use MCP, mutate Git, create pull requests, or merge pull requests.

Human review remains required before any draft proposal can become a real vault file.

## Future Flow

Future supervised workflows must follow this shape:

1. A human or approved controller submits an agent workflow request.
2. The policy classifies the agent identity, action, mode, and branch boundary.
3. Blocked actions stop immediately.
4. Allowed actions remain proposal or request records.
5. Runtime Truth evidence records the policy decision.
6. Agent sandbox reports may be rendered in memory for review.
7. Draft proposals may be built in memory for human review.
8. Human approval remains required before any later supervised action can proceed.

## Branch Boundary

`main` is protected by policy. Push, merge, direct edit, and automatic merge actions targeting `main` are always blocked.

PR open requests may be proposed only from non-main head branches. Base branch may be `main`, but merge remains blocked.

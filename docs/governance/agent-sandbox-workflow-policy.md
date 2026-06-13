---
title: Agent Sandbox Workflow Policy
status: draft
owner: omni
created: 2026-06-13
updated: 2026-06-13
tags:
  - governance
  - sandbox
  - agents
---

# Agent Sandbox Workflow Policy

## Purpose

Phase 10 defines policy and validation for future supervised agent workflows inside the governed sandbox.

This phase does not execute agents, call providers, call MCP, run shell commands, edit files, write vault notes, open pull requests, or mutate Git state.

Phase 11 adds the Agent Runtime Truth Contract. It converts agent workflow policy decisions into structured evidence records only.

Phase 12 adds the Agent Sandbox Report Renderer. It converts Agent Runtime Truth evidence into safe Markdown strings and suggested metadata only.

## Agent Identities

Supported policy identities are plain values only:

- `omni`: governance, routing, Runtime Truth, approval boundary.
- `hermes`: analysis, planning, risk review.
- `aider`: supervised code editing proposal.
- `codex`: investigation, command proposal, code review proposal.
- `claude`: optional code review or planning proposal.
- `unknown`: blocked by default.

## Workflow Modes

- `disabled`: default mode. All workflow actions are blocked.
- `advisory_only`: permits planning and proposal actions only.
- `supervised_sandbox`: permits supervised request actions only.
- `pr_proposal_only`: permits PR title/body/open requests under branch policy.
- `blocked`: explicitly blocks all workflow actions.

## Core Rules

- Direct execution is blocked.
- Direct file editing is blocked.
- Push to `main` is blocked.
- Merge to `main` is blocked.
- PR merge actions are blocked.
- Provider calls and network fetches are blocked.
- MCP write and vault write actions are blocked.
- Runtime Truth is required for future supervised actions.
- Sandbox governance is required before future supervised execution.
- Human approval remains required.

## Agent Runtime Truth Contract

Agent Runtime Truth records policy decisions before any later supervised capability can be considered. The record captures the agent identity, requested action, workflow mode, branch boundary, policy outcome, governance decision, and safety flags.

The contract is evidence-only:

- It does not execute agents.
- It does not execute commands.
- It does not call providers.
- It does not use MCP.
- It does not write vault notes.
- It does not mutate Git.
- It does not create or merge pull requests.

Unsafe or inconsistent evidence maps to `blocked`. This includes any evidence that claims command execution, network access, provider calls, MCP writes, vault writes, merge permission, unprotected `main`, or direct modification of `main`.

Human approval remains required for supervised actions, even when the policy allows a request or proposal.

## Autonomy Operating Model

Phase 15 defines autonomy levels for future agent work. The model permits advisory actions first, then branch-only proposals, test/commit/branch-push requests, PR opening, CI repair, conditional PR merge, supervised sandbox execution, and full autonomous resolution only when the matching level and all safety gates allow it.

The model remains policy-only. It does not execute agents, run commands, call providers, use MCP, write vault notes, mutate Git, create pull requests, or merge pull requests.

## Agent Sandbox Report Renderer

Agent Sandbox Reports are rendered in memory only. The renderer may return Markdown content, a suggested filename, and a suggested vault path, but the suggested vault path is metadata only.

The renderer does not write files, execute agents, execute commands, call providers, use MCP, write vault notes, mutate Git, create pull requests, or merge pull requests.

Reports may later be proposed as draft notes through the governed vault write policy. That later proposal still requires human review and must not bypass approval.

## Public Demo Boundary

Public demos must not enable agent execution. They may show policy decisions, blocked states, and governance flows only.

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

## Public Demo Boundary

Public demos must not enable agent execution. They may show policy decisions, blocked states, and governance flows only.

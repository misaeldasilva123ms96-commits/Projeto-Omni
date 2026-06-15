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

## Phase 11 Agent Runtime Truth

Phase 11 records agent workflow policy decisions as Runtime Truth evidence. The contract stores policy outcome fields, safety flags, branch protection state, and the governance decision.

This phase remains evidence-only. It does not execute agents, execute commands, call providers, use MCP, write vault notes, mutate Git, create pull requests, or merge pull requests.

Unsafe or inconsistent evidence is blocked by default. Push and merge to `main` remain blocked, and human approval remains required for supervised actions.

## Phase 12 Agent Sandbox Reports

Phase 12 renders Agent Runtime Truth evidence as Markdown report content in memory. It returns suggested metadata only, including a safe filename and suggested vault path.

No files are written in this phase. No agents are executed, no commands are executed, no providers are called, no MCP capability is used, no vault notes are written, and no Git state is mutated.

Reports can later be proposed as draft notes through the governed write policy, but human review remains required.

## Phase 14 Human Approval Gate

Phase 14 adds a Human Approval Gate for governed in-memory proposals. It decides whether a proposal may be presented to a human reviewer.

The gate does not approve automatically, write files, create vault notes, change note status, promote drafts to reviewed or approved, execute agents, execute commands, call providers, use MCP, mutate Git, merge pull requests, or push to `main`.

## Phase 15 Autonomy Operating Model

Phase 15 defines controlled full autonomy as a future operating model. It introduces autonomy levels from read-only inspection through full autonomous resolution, but it remains policy-only in this phase.

The model allows future branch work, approved tests, scoped commits, branch pushes, PR opening, CI repair, and conditional PR merge only when all gates pass. Push to `main` remains blocked. Merge to `main` is only policy-defined through PR, with green checks and no exception triggers.

Runtime Truth and reports are mandatory for autonomous future actions. Public demos must not enable unrestricted autonomy.

## Phase 16 Safe Command Execution Gate

Phase 16 adds command request classification for future sandbox execution. The
gate can identify read-safe commands and branch-write commands that may become
future eligible under `sandbox_allowed` mode.

It does not execute commands, start processes, write files, mutate Git, call
networks, call providers, use MCP, create PRs, or merge PRs. Push to `main`,
force push, merge commands, network commands, secret access, production deploys,
billing commands, and destructive commands remain blocked.

## Phase 31 CI Repair Loop Gate

Phase 31 adds a CI Repair Loop Gate that decides whether a failed or
inconclusive CI monitor result from Phase 30 is eligible for a future repair
loop.

The gate classifies CI failure categories into safe (test, typecheck, lint,
format, build) and blocked (security, secret, deployment, billing, permission,
unknown infrastructure). It enforces a repair attempt budget (default max 3)
and validates PR/repository/branch/SHA safety.

This phase does not start repair loops, download logs, retry or trigger
workflows, call providers or agents, create patch proposals, apply patches,
edit files, execute commands, mutate Git, commit, push, update PRs, merge,
or auto-merge.

When eligible, the gate routes to a future `ci_repair_planner` phase. When CI
passes, it routes to `merge_gate`. When CI is pending, it routes to
`wait_for_ci`. Blocked results require human review.

Runtime Truth is generated with governance decision, failure categories,
attempt budget, and child evidence references.

## Phase 32 CI Repair Planner

Phase 32 adds a CI Repair Planner that creates structured repair plan metadata
from safe Phase 31 CI Repair Loop Gate evidence. It is the bridge between CI
failure detection and future automated patch proposal — it plans *what* to fix
without fixing anything.

The planner operates in four modes: `disabled` (default), `dry_run`,
`plan_repair`, and `blocked`. In `plan_repair` mode, it classifies failure
categories (test, typecheck, lint, format, build), enforces the repair attempt
budget (default max 3), detects secrets in check names, and builds repair plan
steps with suggested validation commands and affected area metadata.

This phase does **not** execute repair, edit files, apply patches, download
logs, retry or trigger workflows, call providers or agents, commit, push,
update PRs, merge, or use subprocess/shell/gh.

When the repair plan is ready, `next_allowed_phase` routes to
`scoped_ci_patch_proposal_gate`. When CI passed, it routes to `merge_gate`.
When CI is pending, it routes to `wait_for_ci`. Blocked results route to
`human_review`. Runtime Truth is generated with governance decision, plan
metadata, steps, and affected areas.

## Phase 33 Scoped CI Patch Proposal Gate

Phase 33 adds a Scoped CI Patch Proposal Gate that decides whether a safe
Phase 32 CI repair plan is eligible for a future scoped CI patch proposal
phase. It is a gate only — it does not create patch proposals, generate
patch hunks, apply patches, inspect source files to infer edits, edit
files, write source files, execute repair, download logs, retry or trigger
workflows, call providers or agents, call MCP, execute commands, mutate
Git, commit, push, update PRs, merge, or enable auto-merge.

The gate operates in four modes: `disabled` (default), `dry_run`,
`evaluate_patch_proposal`, and `blocked`. In `evaluate_patch_proposal`
mode, it validates Phase 32 repair plan evidence, validates repair plan
steps (allowed: propose_scoped_*, inspect_*, request_human_review),
classifies candidate target areas and file roots, validates suggested
validation commands as metadata only, enforces patch proposal scope limits
(max files 1-10, max hunks 1-50, max per file 1-20), enforces repair
attempt budget (max 1-10, default 3), and produces eligibility metadata.

When eligible, `next_allowed_phase` routes to `scoped_ci_patch_proposal`.
When CI passed, it routes to `merge_gate`. When CI is pending, it routes
to `wait_for_ci`. Blocked results require human review.

All action flags (`can_create_patch_proposal`, `can_generate_patch_hunks`,
`can_apply_patch`, `can_write_files`, `can_commit`, `can_push`,
`can_update_pr`, `can_merge`, `can_auto_merge`) remain false. Runtime
Truth is generated with governance decision, validated steps, candidate
areas, scope limits, and child evidence references.

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

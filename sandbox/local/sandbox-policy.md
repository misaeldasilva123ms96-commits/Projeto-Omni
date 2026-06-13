---
title: Local Sandbox Policy
status: draft
owner: omni
created: 2026-06-10
updated: 2026-06-10
tags:
  - sandbox
  - governance
  - policy
---

# Local Sandbox Policy

## Purpose

This policy defines the initial boundaries for the local governed sandbox. The sandbox is a future execution
boundary for safe validation, but this phase adds only documentation and configuration scaffolding.

Phase 4 adds a command policy classifier for future sandbox execution planning. The classifier evaluates command
text only. It does not execute commands, call MCP, invoke agents, make network requests, or change runtime
behavior.

Phase 5 records sandbox policy decisions as Runtime Truth evidence. Evidence captures the command text,
normalized command, policy decision, governance decision, and safety defaults. It still does not execute
commands, call MCP, invoke agents, or enable runtime integration.

Phase 6 renders Markdown sandbox reports from Runtime Truth evidence. Reports are returned as content plus a
suggested vault path only. This phase does not automatically write reports to the vault, and human review is
required before saving reports as governed knowledge.

## Allowed Categories

Allowed categories are limited to reviewed local validation:

- Git inspection, such as `git status`, `git diff`, and `git diff --check`.
- Static documentation validation.
- Tests that do not require secrets, provider credentials, production services, or network access.
- Docker compose configuration validation.
- Future sandbox reports written through a reviewed process.

## Blocked Categories

Blocked categories include:

- Direct push or merge to `main`.
- PR merge commands.
- Secret reads or environment dumps.
- Host SSH access.
- Host home directory access.
- Destructive filesystem commands.
- Production deployment commands.
- Package publication commands.
- Token-bearing network calls.
- MCP mutation.
- Agent execution automation.
- Runtime integration without a separate approved implementation task.

## Secret Handling

The sandbox must not receive real secrets, API keys, tokens, passwords, JWTs, private keys, credentials, `.env` values, session cookies, or recovery codes.

Only placeholder names are allowed. Example placeholders must not be valid credentials.

Do not read local `.env` files. Do not print environment dumps. Do not mount host secret directories.

## Network Policy

The initial compose scaffold disables container networking with `network_mode: "none"`.

Future network access requires:

- Written use case.
- Approved target.
- No credential-bearing requests unless a later governance policy explicitly permits them.
- Audit record.
- Human approval.

## Git Policy

Allowed:

- Read-only status and diff inspection.
- Branch verification.
- Whitespace validation.

Blocked:

- Direct push to `main`.
- Direct merge to `main`.
- PR merge from the sandbox.
- History rewriting commands unless explicitly approved outside the sandbox workflow.

## Filesystem Policy

The initial container has no host project mount by default and uses a read-only filesystem with temporary `/tmp`.

Future mounts must be reviewed and constrained. Do not mount:

- User home directories.
- `~/.ssh`.
- `~/.gitconfig`.
- Credential stores.
- Local `.env` files.
- Any directory known to contain secrets.

## Runtime Truth Future Integration

Future Runtime Truth integration may record evidence-backed sandbox reports. Reports must separate facts,
interpretations, and decisions. Reports must not contain secrets or unredacted sensitive logs.

Phase 5 evidence is limited to policy classification records. `execution_attempted` and `command_executed`
remain false because command execution is still future and blocked.

Phase 6 report rendering uses those evidence records to produce Markdown for review. The suggested vault path is
metadata, not an automatic write.

## Governance Future Integration

Future governance integration must require proposal, approval, scoped execution, audit output, and human review before results are accepted.

## MCP Read-Only Future Policy

MCP is intentionally not enabled in this phase. Any future MCP capability must start read-only, must be scoped to approved knowledge sources, and must not write files or execute commands.

## Agent Future Policy

Hermes may coordinate future sandbox context after governance approval.

Aider may assist with implementation only when implementation is explicitly approved.

Codex may inspect, document, and validate within approved boundaries.

No agent may bypass command allowlists, denylist rules, human approval, or the no-main policy.

Phase 10 defines the agent workflow policy boundary. Agents are policy identities only. Advisory actions may be classified as proposals, supervised sandbox actions may be classified as requests, and PR actions may be classified as proposals. The policy does not execute agents, run commands, edit files, push branches, merge PRs, call providers, call network APIs, write vault notes, or enable MCP writes.

Phase 11 adds Agent Runtime Truth evidence for those agent workflow policy decisions. The evidence records the decision only. It does not execute agents, execute commands, call providers, use MCP, write vault notes, mutate Git, create pull requests, or merge pull requests.

Unsafe or inconsistent agent evidence must map to blocked. Push and merge to `main` remain blocked, and human approval remains required for supervised actions.

Push to `main`, merge to `main`, direct file edits, command execution, provider calls, network fetches, vault writes, MCP writes, test disabling, and CI threshold lowering are blocked.

## Public Demo Restrictions

Public demos must use sanitized examples only. Do not demo with real secrets, private logs, production services,
or unreviewed provider accounts.

Do not claim runtime enforcement, MCP support, or agent automation exists until those capabilities are implemented and approved.

## Human Approval Boundaries

Human approval is required for:

- Any write beyond documentation/config scaffolding.
- Any runtime or backend behavior change.
- Any network access.
- Any provider experiment.
- Any test that requires credentials.
- Any new filesystem mount.
- Any PR merge.

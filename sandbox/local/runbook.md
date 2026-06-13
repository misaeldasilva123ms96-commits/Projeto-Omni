---
title: Local Sandbox Runbook
status: draft
owner: omni
created: 2026-06-10
updated: 2026-06-10
tags:
  - sandbox
  - runbook
---

# Local Sandbox Runbook

## Prepare The Sandbox

1. Confirm the current branch is not `main`.
2. Review `sandbox/local/sandbox-policy.md`.
3. Review `sandbox/local/allowlist.commands.json`.
4. Review `sandbox/local/denylist.commands.json`.
5. Confirm no real secrets are present in sandbox files.
6. Validate compose configuration before running any container.

```bash
git status --short
git branch --show-current
docker compose -f sandbox/local/docker-compose.yml config
```

## Run Safe Validation Commands

Start with read-only inspection:

```bash
git status
git diff
git diff --check
```

Run tests only when they are approved, local, and do not require secrets:

```bash
npm test
npm run test:security
npm run test:js-runtime
python -m pytest
pytest
cargo test
```

Do not run install commands or modify lockfiles unless a separate task explicitly approves that scope.

Phase 4 policy classification can be used to evaluate command text before any future sandbox execution workflow.
Classification is not execution and does not grant permission to run a command by itself.

Phase 5 can record those classification decisions as Runtime Truth evidence. Evidence records the policy result
and governance decision only. It does not execute the command.

Phase 6 can render Runtime Truth evidence into Markdown sandbox report content and a suggested vault path. The
renderer does not save files automatically. A human must review and intentionally save any report that becomes
governed vault knowledge.

Phase 12 can render Agent Runtime Truth evidence into Markdown agent sandbox report content and suggested
metadata. The suggested vault path is metadata only. The renderer returns strings in memory only and does not
write files, execute agents, execute commands, call providers, use MCP, write vault notes, mutate Git, create
pull requests, or merge pull requests.

Phase 13 can validate rendered reports against the governed draft write policy and return in-memory draft
proposal objects. It does not create vault notes, write files, mutate the vault, execute commands, call
providers, use MCP, execute agents, mutate Git, create pull requests, or merge pull requests.

Phase 7 can read reviewed Markdown notes from the vault for safe local context inspection. This is read-only
classification and retrieval. It does not write vault files, create reports, call MCP, execute commands, contact
providers, or connect to agent automation.

Phase 8 can classify future MCP vault operation names against a read-only policy. MCP remains disabled by
default. The policy does not start MCP, connect to MCP, call providers, call network APIs, execute commands, or
write vault files.

Phase 9 can classify future governed vault draft-write proposals. It does not write files. It only allows draft
proposal decisions in `draft_only` mode and keeps writing disabled by default. Automation cannot approve notes,
edit approved or reviewed notes, modify ADRs, modify governance policies, or enable MCP write access.

## Check The Branch

Use:

```bash
git branch --show-current
```

If the branch is `main`, stop. Do not modify, push, or merge.

## Verify No Secrets Are Present

Use reviewed secret scanning commands that do not print local secret values.

Allowed examples:

```bash
git diff -- sandbox/local
git diff --check
```

Do not run:

```bash
cat .env
type .env
env
printenv
```

## Verify No Main Merge Or Push Happened

Use read-only Git inspection:

```bash
git status --short
git branch --show-current
git log --oneline --decorate -5
```

Do not run:

```bash
git push origin main
git merge
gh pr merge
```

## Produce A Sandbox Report Later

When governed reporting is approved, create a report under the approved vault or sandbox report path using the
sandbox report template.

Phase 6 report rendering may suggest a path under `vault/09_Sandbox_Reports/`, but that suggestion is metadata
only until a human review approves saving the report.

Phase 12 agent report rendering follows the same boundary. It may suggest a report path, but it does not create
or save a vault note.

Phase 13 draft proposals are still metadata and content in memory. Human review is required before any proposal
becomes a real vault file.

The report should include:

- Branch.
- Date.
- Policy decision evidence.
- Governance decision.
- Execution attempted.
- Command executed.
- Commands reviewed.
- Commands run.
- Evidence collected.
- Secret review.
- Main branch review.
- Result.
- Follow-up actions.

Do not include real secrets, raw `.env` values, unredacted logs, or credentials.

## What Not To Do

- Do not modify `main`.
- Do not push to `main`.
- Do not merge to `main`.
- Do not mount host secrets.
- Do not mount `~/.ssh`.
- Do not mount user home directories.
- Do not read local `.env` files.
- Do not enable MCP.
- Do not add agent execution automation.
- Do not change backend runtime behavior.
- Do not run destructive commands.

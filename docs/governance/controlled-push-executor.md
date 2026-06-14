---
title: Controlled Push Executor
phase: 26
status: draft
owner: Omni Governance
---

# Controlled Push Executor

Phase 26 adds the Controlled Push Executor. It is the first governed layer that may perform a real branch push.

The executor is denied by default. It requires clean Phase 25 Controlled Push Gate evidence and clean Phase 24 commit evidence before any push is attempted.

## Allowed Git Operations

The executor may use only a fixed Git allowlist:

- `git rev-parse --abbrev-ref HEAD`
- `git rev-parse HEAD`
- `git status --short`
- `git push origin <safe_branch>:refs/heads/<safe_remote_branch>`

The implementation must use argv lists, `shell=False`, explicit workspace root, bounded output, timeout, and redaction.

## Blocked Behavior

The executor must not:

- force push
- push `main`
- push protected release or production branches
- create branches
- checkout or switch branches
- stage files
- commit files
- open pull requests
- merge or rebase
- edit files or apply patches
- call providers, MCP, agents, or Vault writes

## Governance Requirements

Every attempt generates Runtime Truth with the Phase 25 push gate evidence and Phase 24 commit evidence linked as child evidence.

Human intervention is required for:

- secrets or credential-like content
- main branch targets
- force push metadata
- protected branch targets
- dirty status containing protected or secret-like files
- unsafe source evidence
- remote mismatch or non-origin remotes

Public demos must not enable unrestricted push automation.

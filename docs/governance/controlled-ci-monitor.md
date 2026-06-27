---
title: Controlled CI Monitor
phase: 30
status: draft
owner: Omni Governance
---

# Controlled CI Monitor

Phase 30 adds the Controlled CI Monitor. It is the first real CI/check status read layer in the Omni Governed Knowledge Sandbox.

The monitor requires clean Phase 29 CI Monitor Gate evidence, a created PR, an open or draft-open PR state, a safe non-main head branch, `base_branch: main`, and a safe head SHA.

## Allowed Behavior

- Read GitHub Actions/check status through narrow injected read-only clients.
- Normalize check status into `passed`, `failed`, `pending`, or `inconclusive`.
- Produce Runtime Truth for every monitoring attempt.
- Route passing CI to a future merge gate as metadata only.
- Route failing CI to the CI Repair Loop Gate (Phase 31) as metadata only.

## Blocked Behavior

- No log download.
- No workflow retry.
- No workflow trigger.
- No repair loop execution.
- No PR creation, update, approval, merge, or auto-merge.
- No push, force push, branch creation, checkout, rebase, or Git mutation.
- No shell commands, `gh`, subprocess, provider calls, MCP, agents, Vault writes, code editing, patch application, or source file writing.

## Human Intervention

Human intervention is required for closed or merged PRs, protected branches, unsafe repositories, missing or unsafe SHA metadata, secret-like content, unexpected CI evidence from Phase 29, or any evidence that earlier phases performed monitoring, log download, retry, merge, push, provider/MCP/agent use, or Vault writes.

## Public Demo Restriction

Public demo mode must not enable unrestricted CI monitoring automation. Only bounded read-only status snapshots are allowed, and all downstream actions remain separate gated phases.

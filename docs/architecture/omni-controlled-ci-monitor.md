---
title: Omni Controlled CI Monitor Architecture
phase: 30
status: draft
owner: Omni Architecture
---

# Omni Controlled CI Monitor

Phase 30 sits after the CI Monitor Gate in the autonomous resolution loop:

`PR created -> CI monitor gate -> controlled CI monitor -> future repair-loop gate or merge gate`

## Inputs

- Phase 29 `ci_monitor_gate_result`
- Optional Phase 28 `pr_creator_result`
- Optional Phase 27 `pr_creation_gate_result`
- Repository, PR number, PR URL, PR state, head branch, base branch, and head SHA metadata
- Narrow injected GitHub Actions and CircleCI read clients

## Client Boundary

The runtime does not hardcode tokens, read `.env`, call arbitrary URLs, or dispatch arbitrary provider methods. Tests use fake clients. Production adapters, if added later, must expose only read-only status/check/workflow snapshot methods.

## Output

The monitor returns a structured result with:

- Observed checks and workflows
- Required, missing, successful, pending, failing, skipped/neutral, and unknown checks
- Aggregate status and conclusion
- Routing metadata for future repair or merge gate phases
- Runtime Truth event `sandbox.ci_monitor.monitor`

## Safety Guarantees

- No command execution or direct subprocess usage.
- No `gh` behavior.
- No Git mutation, push, commit, merge, rebase, checkout, switch, or branch creation.
- No PR update, approval, merge, or auto-merge.
- No log download, workflow retry, workflow trigger, or repair loop.
- No provider/MCP/agent/Vault write integration.
- No code editing, patch application, or source file writing.

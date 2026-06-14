---
title: Controlled PR Creator
phase: 28
status: draft
owner: Omni Governance
---

# Controlled PR Creator

Phase 28 adds the Controlled PR Creator. It is the first governed layer that may create a real pull request.

The creator requires clean Phase 27 PR Creation Gate evidence and pushed non-main branch evidence. It defaults to draft PR creation and records Runtime Truth for every attempt.

## Allowed Capability

The only allowed external capability is a narrow injected GitHub client for:

- duplicate open PR lookup for the same repository, head, and base
- controlled pull request creation with repository, title, body, head, base, and draft fields

The runtime must not hardcode tokens, read `.env`, expose authorization headers, use `gh`, use subprocess, or dispatch arbitrary GitHub methods.

## Next Gate

Phase 29 introduces the CI Monitor Gate. It consumes clean PR creator evidence and decides whether a created PR is eligible for future CI/check monitoring. Phase 29 remains metadata-only and does not call GitHub APIs, CircleCI APIs, download logs, retry workflows, or start repair loops.

## Blocked Behavior

The creator must not:

- merge or enable auto-merge
- approve PRs
- push or mutate Git
- execute commands
- edit files or apply patches
- add labels, request reviewers, or assign users in this phase
- call providers, MCP, agents, Vault writes, or arbitrary network endpoints

## Human Intervention

Human intervention is required for unsafe evidence, main or protected branches, unsafe repositories, duplicate PR risk when not safely modeled, secret-like content, unsafe title/body text, or unsafe labels/reviewers/assignees.

Public demos must not enable unrestricted PR creation automation.

---
title: PR Creation Gate
phase: 27
status: draft
owner: Omni Governance
---

# PR Creation Gate

Phase 27 adds the PR Creation Gate for the Omni Governed Knowledge Sandbox.

The gate decides whether a pushed non-main branch is eligible for a future PR creation phase. It creates PR eligibility metadata, a PR plan, required pre-PR checks, and Runtime Truth.

## Non-Creation Rule

This phase does not create pull requests. It does not call GitHub APIs, execute `gh`, contact GitHub, execute commands, mutate Git, push, merge, rebase, edit files, apply patches, call providers, call MCP, call agents, or write to the Vault.

The following capability flags remain false:

- `can_create_pr`
- `can_merge`
- `can_auto_merge`
- `can_push`
- `can_force_push`
- `can_push_main`
- `can_rebase`
- `can_create_branch`
- `can_checkout`

## Required Evidence

PR eligibility requires clean Phase 26 Controlled Push Executor evidence. Phase 25 push gate evidence may also be supplied and must be clean when present.

The gate blocks missing push evidence, missing pushed refs, missing remotes, missing commit SHA, unsafe Runtime Truth, source branch `main`, protected branches, unsafe repository metadata, unsafe title/body text, unsafe labels, unsafe reviewers, unsafe assignees, and duplicate PR risk.

## Human Intervention

Human intervention is required for secret-like content, protected branches, duplicate PR risk, unsafe repositories, main source branches, or any upstream evidence showing PR creation, merge, rebase, checkout, branch creation, provider, MCP, agent, Vault, or main mutation activity.

Public demos must not enable unrestricted PR automation.

## Phase 28 Handoff

Phase 28 introduces the Controlled PR Creator. It consumes clean Phase 27 evidence and may create a draft PR through a narrow injected GitHub client. Phase 27 remains metadata-only and never creates the PR itself.

---
title: Omni Controlled Push Executor
phase: 26
status: draft
owner: Omni Architecture
---

# Omni Controlled Push Executor

The Controlled Push Executor moves Omni from push eligibility metadata to a governed branch push.

It executes only after:

- Phase 24 has created a commit on a non-main branch.
- Phase 25 has marked the branch eligible for push.
- Runtime Truth from both phases is clean.
- The current branch is verified by Git and matches provided metadata.

## Execution Boundary

The executor does not run arbitrary commands. It does not accept free-form shell text. It constructs the final ref internally as:

```text
<safe_branch>:refs/heads/<safe_branch>
```

Only `origin` is allowed in this phase.

## Safety Model

The executor blocks:

- `main` and protected branches
- force push refspecs
- non-origin remotes
- branch metadata mismatch
- source evidence with PR, merge, rebase, checkout, branch creation, provider, MCP, agent, Vault, or main activity
- secret-like branch, remote, metadata, status, stdout, or stderr content

## Runtime Truth

Runtime Truth records:

- push attempt and outcome
- pre-push and post-push HEAD
- fixed Git operations attempted and completed
- pushed remote and ref
- child evidence from the push gate and commit executor

The executor may set `push_executed`, `git_mutated`, and `network_used` true only after the controlled push succeeds. It must keep PR, merge, rebase, branch creation, checkout, provider, MCP, agent, Vault, and main mutation flags false.

## Phase 27 Boundary

The next layer is the PR Creation Gate. It reviews the pushed branch metadata and Runtime Truth from this executor, but remains metadata-only. Actual PR creation belongs to a later executor phase and must revalidate repository, branch, title, body, labels, reviewers, assignees, and secret safety before any GitHub mutation.

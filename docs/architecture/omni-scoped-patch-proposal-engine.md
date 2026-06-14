# Omni Scoped Patch Proposal Engine Architecture

Phase 20 adds an in-memory proposal layer between the Autonomous Repair Planner and any future patch application phase.

```text
Phase 18 validation result
  -> Phase 19 repair plan
  -> Phase 20 scoped patch proposal
  -> future governed patch application phase
```

Phase 20 does not apply the final arrow. It creates metadata only.

## Responsibilities

The Scoped Patch Proposal Engine consumes Phase 19 repair plans, accepts caller-provided file scope metadata, accepts optional caller-provided file context, produces scoped patch proposal objects, creates intent-only hunks when file context is absent, creates bounded snippet metadata when file context is explicitly supplied, carries safe validation commands as metadata, emits Runtime Truth evidence, and escalates high-risk or secret-bearing requests.

## Non-Responsibilities

The engine does not apply patches, edit code, write files, execute commands, mutate Git, create branches, create commits, push, open pull requests, merge, rebase, call network services, call providers, use MCP, call external agents, write Vault entries, or read source files from disk.

## Core Modules

- `patch_proposal.py`: classification and proposal builder.
- `patch_proposal_types.py`: request and result dataclasses.
- `patch_proposal_truth.py`: Runtime Truth evidence builder.
- `test_scoped_patch_proposal_engine.py`: focused behavior and safety tests.

## Data Model

The request carries repair plan metadata, repair category, failure classification, proposal mode, branch metadata, allowed files, blocked files, suspected files, proposed repair steps, validation commands, optional file contexts, and capability flags.

The result carries proposal status, patch scope, patch complexity, risk level, considered files, proposed files, blocked files, patch proposal metadata, validation metadata, locked capability flags, Runtime Truth, and redaction status.

## Runtime Truth Contract

Runtime Truth event type is `sandbox.patch_proposal.plan`.

The evidence records false for code edited, patch applied, files written, command executed, Git mutated, pull request created, pull request merged, network used, provider called, agent called, MCP used, Vault written, and main modified.

Governance decisions are:

- `blocked`
- `dry_run`
- `patch_proposal_created`
- `requires_human_intervention`

## File Scope

The proposal engine treats paths as metadata. It does not verify file existence and does not read file contents from disk.

Safe proposal scopes include backend, frontend, tests, docs, sandbox local policy, and vault templates. Governance, security, ADR, CI, production, billing, credential, private-key, traversal, repository-internal, and absolute outside-repository scopes are blocked or escalated.

## Validation Metadata

Validation commands are filtered to known safe families and are never executed by this phase. Mutation, GitHub CLI, network, deploy, destructive, and secret-reading commands are removed from validation metadata.

## Public Demo Restriction

Public demo surfaces may show proposal metadata after governance filtering. They must not expose patch application controls or unrestricted command execution.

Phase 21 consumes the proposal output and performs controlled branch patch application only inside an explicit non-main workspace.

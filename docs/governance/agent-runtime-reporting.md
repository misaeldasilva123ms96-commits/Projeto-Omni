---
title: Agent Runtime Reporting
status: draft
owner: omni
created: 2026-06-13
updated: 2026-06-13
tags:
  - governance
  - sandbox
  - agents
  - runtime-truth
---

# Agent Runtime Reporting

## Purpose

Phase 12 adds the Agent Sandbox Report Renderer for Agent Runtime Truth evidence.

Reports are rendered in memory only. The renderer returns Markdown strings and suggested metadata for review. It does not write files, create vault notes, execute agents, execute commands, call providers, use MCP, mutate Git, create pull requests, or merge pull requests.

## Vault Boundary

`suggested_vault_path` is metadata only. It is not an instruction to save a file.

Reports can later be proposed as draft vault notes only through the governed vault write policy. Human review remains required before any report becomes governed knowledge.

## Unsafe Evidence

Reports from unsafe or inconsistent evidence may be rendered for debugging, but they are not allowed for vault draft.

Unsafe evidence includes any claim that an agent was executed, a command was executed, network was used, a provider was called, MCP was used, the vault was written, Git was mutated, `main` was modified, or main branch protection was absent.

## Human Review

Human review remains required for supervised actions and for any later vault draft proposal.

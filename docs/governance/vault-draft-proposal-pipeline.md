---
title: Vault Draft Proposal Pipeline
status: draft
owner: omni
created: 2026-06-13
updated: 2026-06-13
tags:
  - governance
  - vault
  - sandbox
  - runtime-truth
---

# Vault Draft Proposal Pipeline

## Purpose

Phase 13 adds the Governed Draft Proposal Pipeline. It connects rendered reports to the governed draft write policy and returns structured proposal objects in memory.

The pipeline does not write files, create vault notes, mutate the vault, execute commands, execute agents, call providers, use MCP, mutate Git, create pull requests, or merge pull requests.

## Policy Boundary

The pipeline validates draft proposals against the Phase 9 vault write policy.

Allowed proposals are limited to draft-only note types and governed vault paths. `suggested_vault_path` remains metadata only.

Automation cannot set `approved`, `reviewed`, `deprecated`, or `archived` statuses. ADR, governance policy, and security policy edits remain blocked.

## Human Review

Human review is required before any draft proposal becomes a real vault file.

Public demos must not enable vault writing. They may show proposal metadata, blocked states, and review flow only.

## Human Approval Gate

Phase 14 adds a Human Approval Gate for draft proposals. The gate only decides whether a proposal may be presented to a human reviewer.

It does not approve automatically, write files, create vault notes, change note status, promote drafts to reviewed or approved, merge pull requests, push to `main`, or mutate Git.

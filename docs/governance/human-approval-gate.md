---
title: Human Approval Gate
status: draft
owner: omni
created: 2026-06-13
updated: 2026-06-13
tags:
  - governance
  - approval
  - vault
  - sandbox
---

# Human Approval Gate

## Purpose

Phase 14 adds the Human Approval Gate. The gate decides whether a governed proposal may be presented to a human reviewer.

The gate returns approval-gate decisions in memory only. It does not approve automatically, write files, create vault notes, mutate the vault, change note status, promote drafts to reviewed or approved, create pull requests, merge pull requests, push to `main`, execute commands, execute agents, call providers, or use MCP.

## Review Boundary

Only safe draft proposals may be presented for review. The source proposal must already be allowed for human review, allowed by the draft write policy, require human approval, and be allowed for vault draft.

Allowed gate decisions are limited to:

- `submit_for_review`
- `request_changes`
- `reject`
- `hold`

Automation must not return `approved`.

## Blocked Automation

The gate blocks:

- Automatic approval.
- Vault writing.
- Status promotion to `reviewed` or `approved`.
- Final status changes such as `deprecated` or `archived`.
- Pull request merge.
- Push to `main`.
- Governance bypass.
- ADR, governance policy, and security policy edits.

## Human Review

Human approval remains mandatory. A positive gate decision means only that a proposal may be shown to a reviewer; it does not persist approval or write any vault file.

## Autonomy Exception Boundary

Phase 15 keeps human review focused on exceptions. Safe autonomous future actions may proceed only when all gates pass, while secret-like content, skipped tests, CI threshold changes, production impact, billing impact, destructive actions, security policy changes, governance policy changes, and explicit human decisions still require human intervention.

## Public Demo Boundary

Public demos must not enable auto-approval, vault writing, note promotion, PR merge, or push to `main`. Demos may show review eligibility, blocked states, and policy reasoning only.

---
title: Omni Knowledge Vault Index
status: draft
owner: omni
created: 2026-06-09
updated: 2026-06-09
tags:
  - index
  - vault
---

# Omni Knowledge Vault

The Omni Knowledge Vault is the governed knowledge workspace for Projeto Omni. It stores architecture memory, governance records, runtime evidence summaries, incident notes, agent prompt records, provider research, and sandbox reports.

The vault is not runtime code and must not contain real secrets, API keys, tokens, `.env` values, credentials, or copied external project code.

## Navigation

- `01_Roadmap/`: roadmap notes and planning records.
- `02_Architecture/`: architecture notes and system models.
- `03_Runtime_Truth/`: evidence-backed runtime observations.
- `04_Governance/`: policies and decision records.
- `05_Agent_Prompts/`: approved prompt templates and prompt history.
- `06_Incidents/`: incident records and postmortems.
- `07_External_References/`: summarized references and inspiration sources.
- `08_ADR/`: architecture decision records.
- `09_Sandbox_Reports/`: sandbox reports and reviews.
- `10_Provider_Research/`: provider evaluations and comparison notes.
- `templates/`: reusable Markdown templates.

## Core Rules

- Use Obsidian-compatible Markdown.
- Use frontmatter for substantive notes.
- Separate facts, interpretations, and decisions.
- Store redacted summaries instead of sensitive raw logs.
- Do not store secrets.
- Do not add runtime code during documentation-only phases.
- Do not push or merge directly to `main`.

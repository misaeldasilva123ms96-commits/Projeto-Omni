---
title: Omni Knowledge Vault
status: draft
owner: omni
created: 2026-06-09
updated: 2026-06-09
tags:
  - architecture
  - knowledge-vault
  - governance
---

# Omni Knowledge Vault

## Purpose

The Omni Knowledge Vault is the governed knowledge workspace for Projeto Omni. It is designed for architecture memory, runtime evidence, governance decisions, agent prompt records, incidents, provider research, and sandbox reports.

The vault is not a runtime source directory. It is a durable, reviewable knowledge base that can be opened in Obsidian or reviewed through Git.

## Vault Versus Docs

`docs/` contains project-facing documentation intended to explain architecture, roadmap, governance, and security policies to maintainers and reviewers.

`vault/` contains operational knowledge records and templates intended to support day-to-day reasoning, investigations, decision tracking, and future agent workflows.

Use `docs/` for stable explanations and approved policies. Use `vault/` for structured records, evidence, research notes, ADRs, incidents, prompts, and reports.

## Vault Structure

- `00_Index.md`: entry point and navigation map.
- `01_Roadmap/`: planning notes and milestone records.
- `02_Architecture/`: architecture notes and system maps.
- `03_Runtime_Truth/`: evidence-backed runtime observations.
- `04_Governance/`: decision processes and policy records.
- `05_Agent_Prompts/`: approved prompt records and prompt change history.
- `06_Incidents/`: incidents, investigations, and postmortems.
- `07_External_References/`: summarized external references with attribution.
- `08_ADR/`: architecture decision records.
- `09_Sandbox_Reports/`: sandbox review and execution reports.
- `10_Provider_Research/`: provider evaluation records.
- `templates/`: reusable Markdown templates.

## Obsidian-Compatible Markdown Rules

- Use plain Markdown files with `.md` extensions.
- Use YAML frontmatter at the top of notes.
- Use relative links where practical.
- Use Obsidian wiki links only for internal vault notes when the target name is stable.
- Prefer headings over deeply nested bullets.
- Keep one primary topic per file.
- Avoid embedding secrets, credentials, or private customer data.
- Avoid binary attachments unless governance approves a storage rule.

## Frontmatter Conventions

Every substantive vault note should use this shape:

```yaml
---
title: Short Human Title
status: draft
owner: omni
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags:
  - example
---
```

Recommended `status` values:

- `draft`
- `review`
- `approved`
- `deprecated`
- `archived`

Recommended ownership values:

- `omni`
- `hermes`
- `aider`
- `codex`
- `human`

## What Can Be Stored

Allowed:

- Architecture notes.
- ADRs.
- Governance policies.
- Runtime evidence summaries.
- Incident records.
- Public or internally approved provider research.
- Prompt templates that contain no secrets.
- Sandbox reports that contain no sensitive credentials.
- External project references as summaries, links, and architectural inspiration.

Blocked:

- Real secrets, API keys, tokens, passwords, private keys, or credentials.
- `.env` values.
- Unredacted personal data.
- Customer confidential data without explicit approval.
- Runtime source code for this documentation-only phase.
- Copied code from external projects.
- Instructions that bypass governance controls.

## Phase 7 Read-Only Access Layer

The Phase 7 Vault access layer is a local, read-only reader for governed Markdown notes. It can parse approved or reviewed vault notes for safe context preparation, but it does not write files, create indexes, call providers, use MCP, execute commands, or inject context into agents automatically.

Only notes with trusted review status are eligible for context:

- `approved`
- `reviewed`

Notes with `draft`, `review`, `deprecated`, `archived`, missing frontmatter, non-Markdown extensions, path traversal attempts, invalid UTF-8, or secret-like content are blocked from context by default.

The reader returns structured metadata, body text, frontmatter, redaction status, and a blocked reason when applicable. It is an access classification boundary only; human review still governs whether any vault knowledge may be used in a runtime or agent workflow.

## Runtime Truth Evidence Model

Runtime Truth records must distinguish observation from interpretation.

Each record should include:

- Evidence source.
- Collection date.
- Command, log source, or document source when safe to disclose.
- Observed fact.
- Confidence level.
- Reviewer or owner.
- Follow-up action.

Evidence records must not include secrets. When a command or log contains sensitive material, store a redacted summary and note that the raw evidence is held outside the vault under approved access controls.

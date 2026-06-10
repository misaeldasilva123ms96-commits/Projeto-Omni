---
title: Sandbox Threat Model
status: draft
owner: omni
created: 2026-06-09
updated: 2026-06-09
tags:
  - security
  - threat-model
  - sandbox
---

# Sandbox Threat Model

## Scope

This threat model covers the planned Omni Governed Sandbox and its relationship to the Omni Knowledge Vault. It is documentation only and does not implement sandbox controls.

## Assets

- Repository source code.
- Documentation and vault knowledge records.
- Runtime Truth evidence.
- Governance decisions.
- Agent prompts.
- Provider research.
- Secrets and credentials stored outside the vault.
- `main` branch integrity.

## Trust Boundaries

- Human maintainers.
- Agent-assisted documentation and analysis.
- Future MCP read-only access.
- Future governed write access.
- Local development environment.
- External provider documentation and research sources.

## Threats

### Secret Exposure

Risk: an agent, command, log, or report stores or prints real secrets.

Controls:

- No secrets in the vault.
- Redacted examples only.
- No `.env` values in documentation.
- Review before public demos.

### Main Branch Modification

Risk: a command directly pushes or merges to `main`.

Controls:

- Explicit rule: no direct push or merge to `main`.
- Branch-based work only.
- Human review before integration.

### Sandbox Escape

Risk: future sandbox execution accesses files, network targets, or credentials outside approved scope.

Controls:

- Read-only first.
- Least privilege.
- Block destructive commands.
- Block credential access.
- Audit command intent and results.

### External Code Contamination

Risk: copied external project code enters the repository without review or license clarity.

Controls:

- External projects may be used only as architectural inspiration.
- Do not copy external code.
- Record references as summaries and links.

### Unreviewed Writes

Risk: future automation modifies files without approval.

Controls:

- Governed write policy required before write automation.
- Branch-only writes.
- Approved target paths.
- Audit logs and rollback plans.

### False Runtime Truth

Risk: notes present assumptions as observed facts.

Controls:

- Runtime Truth evidence model.
- Separate fact, interpretation, and decision.
- Require evidence source and collection date.

### Public Demo Leakage

Risk: a demo exposes private repository data, logs, credentials, or provider information.

Controls:

- Mock or redacted data only.
- No private logs.
- No real credentials.
- No claims of enforcement before implementation exists.

## Allowed Future Command Categories

- Read-only file inspection.
- Git status and diff inspection.
- Markdown validation.
- Approved tests on non-main branches.
- Approved documentation generation.

## Blocked Future Command Categories

- Direct push or merge to `main`.
- Credential access.
- Secret printing.
- Destructive filesystem changes.
- Production deployments.
- Unapproved network exfiltration.
- Cloud account mutation.
- Execution of downloaded or unreviewed code.

## Testing Checklist

- Confirm branch is not `main`.
- Confirm changes are documentation and vault structure only.
- Confirm no runtime code changed.
- Confirm no secrets were introduced.
- Run `git status --short`.
- Run `git diff --check`.

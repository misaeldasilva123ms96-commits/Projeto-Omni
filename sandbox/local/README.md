---
title: Local Governed Sandbox
status: draft
owner: omni
created: 2026-06-10
updated: 2026-06-10
tags:
  - sandbox
  - local
  - governance
---

# Local Governed Sandbox

## Purpose

The local governed sandbox is a conservative foundation for future isolated Omni validation. It is intended to support safe local experiments for tests, provider research, tool validation, and agent workflows after governance approves those capabilities.

This phase is documentation and configuration scaffolding only.

## What This Is Not

This is not production infrastructure.

This is not the final Omni runtime image.

This is not an MCP server or MCP integration.

This is not an agent execution system.

This is not connected to backend runtime behavior.

This must not receive real secrets, API keys, tokens, JWTs, `.env` values, private keys, credentials, or unredacted sensitive logs.

## Safety Rules

- Do not push directly to `main`.
- Do not merge directly to `main`.
- Do not mount host secrets.
- Do not mount `~/.ssh`.
- Do not mount `~/.gitconfig`.
- Do not mount a user home directory.
- Do not run commands that require secrets.
- Do not enable MCP until a read-only policy is approved.
- Do not enable runtime integration until a separate implementation task is approved.

## Basic Usage

Review the configuration:

```bash
docker compose -f sandbox/local/docker-compose.yml config
```

Build the scaffold image:

```bash
docker compose -f sandbox/local/docker-compose.yml build
```

Start an inert sandbox shell only after reviewing the policy:

```bash
docker compose -f sandbox/local/docker-compose.yml run --rm local-sandbox
```

The default container is intentionally minimal. It does not copy the repository, expose ports, mount host secrets, or run Omni runtime services.

## Next Governance Step

Before any execution automation is added, create a reviewed proposal that defines approved commands, filesystem boundaries, audit logging, Runtime Truth reporting, and human approval requirements.

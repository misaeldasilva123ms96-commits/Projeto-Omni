# Projeto Omni Copilot Agent Instructions

These instructions apply repository-wide to GitHub Copilot agents working on Projeto Omni.

Projeto Omni is a multi-runtime cognitive runtime with Rust, Python, Node.js, and optional frontend components. It includes governance, observability, runtime truth classification, public payload sanitization, CI validation, and strict safety boundaries.

## Branch And Merge Policy

- Agents may edit files when assigned a clear issue or task.
- Agents must create a dedicated working branch before editing files.
- Agents must never work directly on `main`.
- Agents must never push directly to `main`.
- Agents must never merge pull requests.
- Agents must never delete, rewrite, force-push, or otherwise alter protected branches.
- Agents may commit and push only their own task branch.
- Agents may open a pull request targeting `main`.
- Final review, approval, promotion, and merge into `main` are reserved exclusively for the repository owner/user.

Use descriptive branch names, such as:

- `agent/ci-fix-<short-topic>`
- `agent/docs-audit-<short-topic>`
- `agent/security-review-<short-topic>`
- `agent/runtime-investigation-<short-topic>`
- `agent/tests-<short-topic>`

## Scope Control

- Keep changes scoped to the assigned issue.
- Prefer small, reviewable pull requests.
- Avoid broad rewrites unless the issue explicitly requests them.
- Preserve governance and runtime contracts unless the issue explicitly authorizes changing them.
- Preserve public payload safety and sanitization behavior.
- Do not modify `.env` files or secret-bearing configuration.

## Safety Boundaries

Never expose, print, log, or commit:

- secrets, tokens, keys, JWTs, or `.env` contents
- stack traces, raw stdout/stderr, command args, or env vars
- raw provider payloads or raw tool payloads
- local memory content or private runtime artifacts
- private credentials or sensitive local paths

If sensitive data is encountered, report only the file name, field name, or risk category, never the value.

## Required Agent Report

Every agent pull request or final task report must explain:

1. what changed
2. why it changed
3. files modified
4. validation commands and results
5. risk level

## Validation Expectations

- Run the most targeted validation commands for the changed area.
- Do not weaken tests only to make CI pass.
- Report any command that was not run and why.
- If validation fails, report the failing command, concise failure reason, and recommended next step.


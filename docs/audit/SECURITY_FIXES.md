# Security Fixes

## Shell Hardening

Shell execution is deny-by-default, blocked in public demo mode, protected by allowlist checks, and protected by dangerous-pattern rejection. Public blocked results use controlled public error shapes and do not expose raw command output, stack traces, paths, env, or secrets.

## Specialist And Error Logging

Specialist/runtime failures return structured degraded fallbacks. Normal mode does not log raw exception messages, stacks, absolute paths, env, provider payloads, or command output. Internal debug details are sanitized and disabled when public demo mode is active.

## Backend Public Payload Sanitization

Backend runtime inspection and diagnostic payloads are recursively sanitized before public/API exposure. Public views preserve useful fields such as runtime mode, provider status, tool status, request id, warnings, public summary, and public error code/message while removing raw internals.

## Frontend Debug Sanitization

Frontend runtime/debug UI sanitizes incoming payloads defensively before display. It preserves public runtime fields and strips stack, trace, env, token, secret, command, raw payload, provider raw response, tool raw result, and memory raw content.

## Learning And Log Redaction

Learning and runtime logs redact secrets, credentials, PII, local paths, and raw internal payload fields before persistence. Local log/storage directories are gitignored. Historical logs are not rewritten.

## Tool Governance

Sensitive tools are evaluated before execution. Read-sensitive, write, destructive, shell, network, and git-sensitive operations are gated or blocked by governance. Blocked results include public-safe governance audit data and update runtime truth as blocked rather than successful.

## Secrets And Config

Supabase and provider diagnostics expose booleans/status only. Raw keys, URLs, service-role values, provider key prefixes, hashes, lengths, env dumps, and raw config are not public diagnostics. `.env.example` uses placeholders only.

## API Validation And Rate Limiting

The Rust `/chat` boundary validates content type, JSON, message length, body size, unsafe control characters, and bounded request/session identifiers before invoking Python/Node. Rate limiting is enabled by default and feature-flagged.

## Container Demo Mode

`Dockerfile.demo` and `docker-compose.demo.yml` set public demo mode, disable shell/debug internals, enable rate limits, use subprocess defaults, run as non-root, avoid privileged mode, avoid Docker socket mounts, and rely on `.dockerignore` to exclude secrets/logs/artifacts.

## Security Regression Suite

`npm run test:security` consolidates regression checks across shell hardening, logging, payload sanitization, frontend debug, learning redaction, runtime truth, governance, secrets/config, API validation, container posture, and error taxonomy.

# PHASE 5 — INPUT VALIDATION & RATE LIMITING

Date: 2026-05-01

Base branch: security/secrets-config-04

Base commit: 11a623c6acd3d1b6c478c8e039b3239efb7cf14f

Working branch: security/input-rate-limit-05

## Scope

Phase 5 hardens the Rust `/chat` and `/api/v1/chat` public API boundary only. It does not change cognitive runtime behavior, Python/Node orchestration, provider routing, CORS, frontend rendering, or governance semantics.

## Rust/API Paths Hardened

- `backend/rust/src/main.rs`
- `backend/rust/src/observability_auth.rs` test state construction compatibility
- `backend/rust/src/run_control.rs` test state construction compatibility

## Validation Rules

Before invoking Python/Node, the chat handlers now enforce:

- `Content-Type` must be `application/json`.
- Body size must be at most `OMNI_MAX_BODY_BYTES` / `OMINI_MAX_BODY_BYTES`, default `65536`.
- JSON parse failures return a controlled public error.
- `message` must be non-empty after trim.
- `message` length must be at most `OMNI_MAX_MESSAGE_CHARS` / `OMINI_MAX_MESSAGE_CHARS`, default `8000`.
- Unsafe control characters `0x00-0x1F` are rejected except tab, newline, and carriage return.
- `client_session_id` and `request_id` are optional but must be at most 128 characters and match `[A-Za-z0-9_.:-]`.
- Valid request behavior remains unchanged after validation.

## Body Limit Strategy

The handlers now receive raw `Bytes`, validate `bytes.len()` against the configured body limit before JSON parsing, and return a public-safe `PAYLOAD_TOO_LARGE` response without invoking runtime.

## Rate Limiting

Implemented a minimal in-memory sliding-window limiter:

- Store: `HashMap<ClientKey, VecDeque<Instant>>`
- Protection: `Mutex`
- Window: 60 seconds
- Key: `x-forwarded-for` first IP when present, otherwise `global`
- Default enabled: `OMNI_RATE_LIMIT_ENABLED=true`
- Default limit: `OMNI_RATE_LIMIT_PER_MINUTE=30`
- Legacy aliases supported with `OMINI_*`
- `OMNI_*` takes precedence over `OMINI_*`

## Error / Taxonomy Behavior

Rust public error shape:

```json
{
  "error_public_code": "INPUT_VALIDATION_FAILED",
  "error_public_message": "Request input failed validation.",
  "severity": "blocked",
  "retryable": false,
  "internal_error_redacted": true
}
```

Added/normalized Phase 8 taxonomy codes in Python/JS taxonomy modules for consistency:

- `INPUT_VALIDATION_FAILED`
- `PAYLOAD_TOO_LARGE`
- `RATE_LIMITED`
- `INVALID_CONTENT_TYPE`
- `INVALID_JSON`

All error responses are generic and do not include raw request body, stack traces, paths, env, tokens, stdout/stderr, or raw payloads.

## Tests

Added/updated tests for:

- Valid chat request passes and invokes runtime.
- Empty and whitespace-only messages are rejected before runtime.
- Oversized message and oversized body are rejected.
- Invalid JSON and wrong content type are rejected.
- NUL/control chars are rejected.
- Newline/tab are accepted.
- Unsafe `client_session_id` and `request_id` are rejected.
- Valid bounded IDs are accepted.
- Rate limit triggers after configured limit.
- Rate limit can be disabled.
- `OMNI_*` / `OMINI_*` env alias precedence works.
- Rejected validation paths do not invoke Python runtime.
- Public error taxonomy shape remains safe.

## Known Limitations

- The in-memory limiter is per-process and resets on process restart.
- Multi-instance deployments require edge/platform rate limiting for global enforcement.
- Client key uses `x-forwarded-for` when present, otherwise falls back to `global`.

## Rollback

Revert the Phase 5 commit on `security/input-rate-limit-05`. This restores the prior Axum `Json<T>` extractor path and removes the in-memory limiter.

## Gate 5 Status

Status: PASSED. Targeted Rust chat validation/rate-limit tests passed, `cargo test` passed with 38 tests, JS/Python taxonomy checks passed, broad repo commands returned exit 0, Python changed files compiled, and `git diff --check` passed.

## No Merge Into Main

This phase does not merge into main.

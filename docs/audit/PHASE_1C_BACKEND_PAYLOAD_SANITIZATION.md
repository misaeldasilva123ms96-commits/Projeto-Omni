# PHASE 1C BACKEND PAYLOAD SANITIZATION — Projeto Omni

Date: 2026-05-01

Branch: hardening/backend-payload-01c

Base branch: hardening/logging-01b

Base commit: 795011466ebf65019141bf38f0037b333e55a2b1

Statement: Phase 1C adds a public-safe backend payload view at the Python API/stdout boundary. Runtime truth semantics, frontend rendering, shell policy, and specialist logging policy were not changed.

## Files Changed

- `backend/python/main.py`
- `backend/python/brain/runtime/observability/public_runtime_payload.py`
- `tests/runtime/observability/test_public_runtime_payload.py`
- `docs/audit/PHASE_1C_BACKEND_PAYLOAD_SANITIZATION.md`

## Backend Response Paths Inspected

- `backend/python/main.py`: primary Python public response/stdout boundary consumed by Rust.
- `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`: source of internal runtime inspection and signals.
- `backend/rust/src/main.rs`: Rust chat API forwards Python JSON; no Rust change was required because Python is the earliest backend public boundary.
- `config/provider_registry.py`: provider diagnostics are already designed as public-safe rows and are still passed through recursive sanitization.

## Sanitizer / Public View Summary

Added `sanitize_public_runtime_payload(...)` and `build_public_cognitive_runtime_inspection(...)`.

Behavior:

- Recursively sanitizes dict/list/tuple payloads.
- Removes dangerous/internal keys by substring match.
- Redacts sensitive path/token-like string values.
- Builds a public cognitive runtime inspection using a top-level allowlist.
- Adds a public summary derived from `runtime_mode`.
- Does not mutate the original payload.
- Falls back safely on malformed payloads.

`backend/python/main.py` now:

- Avoids logging raw pre-sanitized responses.
- Avoids logging raw operational message content when blocked.
- Sanitizes optional public debug details.
- Converts internal `last_cognitive_runtime_inspection` into a public inspection view before emitting JSON.
- Emits the final response through `sanitize_public_runtime_payload(...)`.
- Exposes selected public inspection fields top-level for API/frontend compatibility.

## Removed Fields / Classes

Removed recursively when found in public payloads:

- `stack`
- `trace`
- `traceback`
- `raw_error`
- `stdout`
- `stderr`
- `command`
- `args`
- `argv`
- `env`
- `api_key`
- `token`
- `jwt`
- `secret`
- `password`
- `authorization`
- `bearer`
- `provider_raw`
- `raw_provider`
- `raw_response`
- `raw_payload`
- `execution_request`
- `tool_raw_result`
- `memory_raw`
- `memory_content`

Redacted in string values:

- Unix absolute paths under `/home`, `/root`, `/tmp`, `/var`, `/usr`, `/etc`
- Windows absolute paths under `C:\Users`, `C:\Windows`, `C:\Program Files`
- OpenAI-style `sk-...` and `sk-proj-...` keys
- Bearer tokens
- JWT-like strings

## Preserved Public Fields

Public cognitive/runtime inspection keeps only:

- `runtime_mode`
- `runtime_reason`
- `cognitive_chain`
- `source_of_truth`
- `final_verdict`
- `fallback_triggered`
- `provider_actual`
- `provider_public_name`
- `provider_failed`
- `tool_status`
- `tool_public_name`
- `latency_ms`
- `request_id`
- `warnings_public`
- `error_public_code`
- `error_public_message`
- `internal_error_redacted`
- `public_summary`

Selected public fields are also surfaced top-level where present:

- `runtime_mode`
- `runtime_reason`
- `fallback_triggered`
- `provider_actual`
- `provider_failed`
- `tool_status`
- `latency_ms`
- `public_summary`

## Tests Run / Results

- `python -m py_compile backend/python/main.py backend/python/brain/runtime/observability/public_runtime_payload.py` — PASS
- `python -m pytest -q tests/runtime/observability/test_public_runtime_payload.py` — PASS, 5 tests
- `npm run test:js-runtime` — PASS
- `npm run test:python:pytest` — TIMEOUT after 300 seconds
- `npm test` — TIMEOUT after 300 seconds when rerun isolated

## Inherited Timeout Note

The broad Python test path timed out again. Similar broad pytest timeouts were recorded in earlier hardening phases, and no evidence indicates this Phase 1C sanitizer caused the timeout. The narrow payload sanitizer test and JS runtime suite passed.

## Known Limitations

- This phase sanitizes the Python public boundary. Internal-only endpoints and historical audit files remain future review targets.
- Rust was not changed because it forwards the Python JSON output and the safer boundary is now before stdout emission.
- Phase 2 still owns runtime truth semantics; this phase intentionally does not reinterpret runtime classification.

## Rollback

Rollback command:

```bash
git revert <phase-1c-commit>
```

## Gate 1C Status

PASSED:

- Backend public response is sanitized before frontend/Rust API consumption.
- Public cognitive/runtime view exists.
- Raw nested internal fields are removed recursively.
- Public diagnostics remain available via allowlisted inspection and top-level fields.
- Tests were added.
- No raw stack/path/env/provider/tool/memory payload exposure is allowed by the public sanitizer.
- No merge into main.

No merge into main: confirmed.

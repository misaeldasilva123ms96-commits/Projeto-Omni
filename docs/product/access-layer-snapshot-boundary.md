# Omni Access Layer Access Snapshot Boundary

This document describes the Phase 6 Access Snapshot boundary foundation. It is
a pure helper layer for building a stable public-safe response envelope around
the Public Runtime Access Snapshot.

## Location

- Boundary: `backend/python/brain/runtime/access_layer/access_snapshot_boundary.py`
- Tests: `tests/runtime/test_access_snapshot_boundary.py`

## Boundaries

This phase does not add a public endpoint, real provider calls, Puter.js
integration, OpenRouter/Gemini/Groq/OpenAI calls, BYOK key storage, billing, UI,
or production brain behavior changes.

The boundary depends on the Phase 5 `PublicAccessSnapshot`, which composes
PlanPolicy, TokenQuota, ProviderRouter, and ProviderRegistry. The boundary only
normalizes public-shaped input, rejects unsafe request-controlled fields, and
returns an exact safe response envelope.

## Public Input Restrictions

Public input may include only controlled `plan_mode`, opaque `subject_id`,
`usage_date`, `tokens_in`, and `tokens_out`.

Public input must never include `policy_overrides`, `provider_mode`,
`provider_family`, selected provider family, quota limits, raw provider config,
provider payloads, API keys, access tokens, credentials, secrets, billing
config, private endpoints, command arguments, or debug data.

`subject_id` is public only as an opaque identifier. Callers must never pass
secrets, account credentials, API keys, email addresses, or raw user tokens as
`subject_id`.

`existing_daily_tokens` remains trusted server-side state supplied outside the
public input mapping. It must not be accepted from a public request payload as an
authoritative quota value.

Unknown plans, invalid token usage, unsafe override attempts, invalid subject
identifiers, and malformed snapshots return fail-closed denied envelopes without
raw exception details, stack traces, or internal error content.

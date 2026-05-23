# Omni Access Layer Public Runtime Access Snapshot

This document describes the Phase 5 Public Runtime Access Snapshot foundation.
It composes PlanPolicy, TokenQuota, ProviderRouter, and ProviderRegistry into a
single public-safe access-layer status object.

## Location

- Contract: `backend/python/brain/runtime/access_layer/public_access_snapshot.py`
- Tests: `tests/runtime/test_public_access_snapshot.py`

## Boundaries

This phase does not add endpoints, real provider calls, Puter.js integration,
OpenRouter/Gemini/Groq/OpenAI calls, BYOK key storage, billing, UI, or
production brain behavior changes.

`subject_id` is an opaque public identifier. `policy_overrides` and
`existing_daily_tokens` are trusted server-side inputs only and must never be
treated as public request-authoritative values.

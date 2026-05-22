# Omni Access Layer TokenQuota Foundation

This document describes the Phase 2 TokenQuota foundation for Omni Access Layer.
It is a contract layer only: it calculates token totals, plan-based daily quota
state, per-request input/output limit flags, and public-safe quota snapshots.

## Dependency

TokenQuota depends on the Phase 1 PlanPolicy foundation as the source of plan
limits. It resolves `free`, `byok`, `pro`, and `internal` policies through
`backend/python/brain/runtime/access_layer/plan_policy.py`.

## Location

- Contract: `backend/python/brain/runtime/access_layer/token_quota.py`
- Tests: `tests/runtime/test_token_quota.py`

## Boundaries

This phase does not add real provider routing, Puter.js, BYOK key storage,
billing, persistence, UI, or provider calls. Daily usage is supplied by the
caller and evaluated deterministically against the resolved PlanPolicy.

`subject_id` is included in public quota snapshots only as an opaque public
identifier. Callers must not pass API keys, credentials, secrets, provider
tokens, or sensitive configuration as the subject identifier.

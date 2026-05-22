# Omni Access Layer ProviderRouter Foundation

This document describes the Phase 3 ProviderRouter foundation for Omni Access
Layer. It produces public-safe provider routing decisions from PlanPolicy and
TokenQuota without calling any real external provider.

## Dependency

ProviderRouter depends on:

- `backend/python/brain/runtime/access_layer/plan_policy.py` for plan and
  provider modes
- `backend/python/brain/runtime/access_layer/token_quota.py` for quota, input,
  and output allowance flags

## Location

- Contract: `backend/python/brain/runtime/access_layer/provider_router.py`
- Tests: `tests/runtime/test_provider_router.py`

## Boundaries

This phase does not add real provider calls, Puter.js integration, BYOK key
storage, billing, UI, or production brain integration. BYOK, Pro, and Internal
routes are contract-level provider-family decisions only.

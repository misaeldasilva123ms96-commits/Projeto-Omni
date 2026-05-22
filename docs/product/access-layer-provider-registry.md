# Omni Access Layer Provider Adapter Registry Foundation

This document describes the Phase 4 Provider Adapter Registry foundation for
Omni Access Layer. It defines public-safe provider adapter metadata and validates
ProviderRouter decisions against known provider families.

## Dependency

ProviderRegistry depends on ProviderRouter decisions, especially
`selected_provider_family` and `provider_mode`. It does not perform routing by
itself and does not call providers.

## Location

- Contract: `backend/python/brain/runtime/access_layer/provider_registry.py`
- Tests: `tests/runtime/test_provider_registry.py`

## Boundaries

This phase does not add real provider calls, Puter.js integration,
OpenRouter/Gemini/Groq/OpenAI calls, BYOK key storage, billing, UI, private
endpoints, provider request payloads, or production brain integration. Registry
records are metadata only and must not contain API keys, secrets, access tokens,
raw credentials, environment variables, internal configuration, or billing
configuration.

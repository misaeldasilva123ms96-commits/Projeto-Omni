# PHASE 4 — SECRETS & CONFIG HARDENING

Date: 2026-05-01

Base branch: runtime/error-taxonomy-08

Base commit: b6e3a8af05dd135477078a6013ae03aaf859bf88

Working branch: security/secrets-config-04

## Scope

Phase 4 hardened public diagnostics and examples around secrets/config only. Runtime provider routing, frontend rendering behavior, shell policy, runtime truth, governance, error taxonomy, and learning flow were not rewritten.

## Paths Inspected

- `storage/memory/supabaseClient.js`
- `storage/memory/runtimeMemoryStore.js`
- `platform/providers/providerRouter.js`
- `backend/python/config/secrets_manager.py`
- `backend/python/config/provider_registry.py`
- `backend/python/brain/runtime/observability/public_runtime_payload.py`
- `frontend/src/lib/runtimeDebugSanitizer.ts`
- `backend/python/brain/runtime/learning/redaction.py`
- `.env.example`
- Supabase/frontend importers and existing tests mapped in `docs/audit/CODEMAP_REMEDIATION_TARGETS.md`

## Changes

- Removed raw `supabaseKey` and `supabaseUrl` exports from the Node Supabase client module.
- Added `getSupabaseClient()` for internal execution without exporting raw config values.
- Normalized Supabase diagnostics to boolean/status fields only: `supabase_configured`, `url_present`, `anon_key_present`, `service_role_present`.
- Removed raw Supabase URL usage from semantic memory metadata by replacing `vector_origin` with the public string `supabase`.
- Added provider diagnostic booleans `key_present` and `model_configured` without exposing key values, prefixes, lengths, hashes, or raw config.
- Extended backend public payload sanitizer, frontend debug sanitizer, and learning redaction to treat `raw_key` and `raw_url` as internal payload fields.
- Updated `.env.example` to placeholder-only values and documented `OMNI_*` canonical / `OMINI_*` legacy compatibility.
- Added `docs/security/secrets-policy.md`.

## Diagnostics Shape

Supabase diagnostics:

```json
{
  "supabase_configured": false,
  "url_present": false,
  "anon_key_present": false,
  "service_role_present": false
}
```

Provider diagnostics remain backward-compatible with operational booleans, but add:

```json
{
  "provider": "openai",
  "configured": true,
  "key_present": true,
  "model_configured": true
}
```

No diagnostic path should expose raw env, raw config, key values, key prefixes, key lengths, key hashes, provider raw payloads, tool raw payloads, memory raw content, `raw_key`, or `raw_url`.

## Tests

Targeted tests were added/updated for:

- Supabase module export safety.
- Supabase boolean-only diagnostics.
- Provider diagnostics without secret-derived fields.
- `.env.example` placeholder-only policy.
- Backend public sanitizer secret/config stripping.
- Frontend debug sanitizer secret/config stripping.
- Learning redaction of provider/Supabase-like secrets.
- `SUPABASE_NOT_CONFIGURED` public error safety.

## Gate 4 Status

Gate 4 requires:

- Supabase raw key/url values are not exported.
- Provider keys are never exposed in diagnostics.
- Diagnostics are public-safe booleans/status only.
- `.env.example` has placeholders only.
- Secrets policy doc exists.
- Tests added/updated.
- No raw secret/config exposure introduced.
- No merge into main.

Status: PASSED with inherited broad-suite timeout notes. Targeted Phase 4 Node/Python/frontend tests passed, Python changed files compiled, and `git diff --check` passed. Broad `npm run test:python:pytest` and `npm --prefix frontend run typecheck` timed out at 300 seconds, matching previously observed inherited timeout behavior from earlier phases.

## Rollback

Revert the Phase 4 commit on `security/secrets-config-04`. This restores previous Supabase exports and diagnostics shape, so rollback should only be used if compatibility issues are confirmed.

## No Merge Into Main

This phase does not merge into main.

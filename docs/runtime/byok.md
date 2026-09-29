# BYOK Boundaries

BYOK means bring your own key. Omni has two distinct credential surfaces: request-scoped session BYOK for chat execution and authenticated persistent provider settings. They are not yet connected into one end-to-end execution path.

## Current Scope

Implemented:

- typed Rust request boundary
- provider allowlist and payload bounds
- private Python bridge extraction
- request-scoped Node env overlay
- fail-closed BYOK execution policy
- cross-language tests for forwarding, isolation, and redaction
- authenticated provider-settings API
- encrypted per-user provider credential storage
- frontend Provider Center for configure, update, delete, and explicit connection tests

Not implemented end to end:

- automatic use of the authenticated user's stored provider credential by the normal chat path
- propagation of authenticated chat identity into `JSRuntimeAdapter.build_env()` credential resolution
- billing, quotas, or hosted BYOK governance
- local URL BYOK overrides

Persistent settings therefore must not be described as executable chat BYOK. Until identity propagation and fallback policy are explicitly wired and tested, chat execution uses either request-scoped `session_provider_credentials` or system environment credentials.

## Request Shape

```json
{
  "message": "Olá",
  "provider_preference": "openai",
  "session_provider_credentials": {
    "openai": {
      "api_key": "<session-only-api-key>",
      "model": "optional-model"
    }
  }
}
```

Allowed BYOK providers:

- `groq`
- `openrouter`
- `openai`
- `anthropic`
- `gemini`
- `ollama`
- `lmstudio`

DeepSeek is rejected.

## Fail-Closed Policy

When `session_provider_credentials` is non-empty:

1. BYOK session mode is active.
2. `provider_preference` is required.
3. `provider_preference` must match a credential entry.
4. Only the selected provider receives the request-scoped credential overlay.
5. The selected session credential overrides the system env credential for that provider only for the current request.
6. If the selected BYOK provider fails, Omni does not fall back to system owner keys or another provider.

Provider preference without `session_provider_credentials` keeps normal system-provider behavior.

## Privacy Rules

Session API keys must not enter:

- public response payloads
- `provider_diagnostics`
- `provider_diagnostics_snapshot`
- runtime truth
- cognitive runtime inspection
- provenance
- debug payloads
- logs
- learning artifacts
- transcript/history stores
- error bodies

Model names are diagnostic metadata, not secrets, but they should appear only in approved model-related fields and not in raw request/credential surfaces.

## Local Provider Limits

For Ollama and LM Studio, P5C only allows request-scoped model/key overlay. It does not accept arbitrary local URLs from the request. Local providers still require `OLLAMA_URL` or `LMSTUDIO_URL` from system configuration.

## Active Credential Checks

Provider Center active credential checks never follow HTTP redirects. Every 3xx
response is rejected before a second network request is issued, including redirects
to another path on the same host. The public result is `redirect_denied`; Location,
credentials, provider bodies and raw exceptions are not returned or logged by the
active-test fallback. The existing five-second transport timeout and fixed official
HTTPS endpoints remain unchanged. This policy is local to active checks and does
not change chat execution or Gemini authentication semantics.

## Encrypted Credential Store v2

AES-256-GCM still uses a 32-byte key. Version 2 binds `credential_id`, `user_id`
and `provider_id` with deterministic JSON AAD (sorted keys, compact separators),
including the domain `omni-credential-store:v2`. Timestamps are administrative
and are not authenticated. Every encryption, update and migration generates a new
random 12-byte nonce. Identity/ciphertext tampering is rejected on decryption.
Unknown versions, malformed records, duplicate IDs and duplicate `(user, provider)`
pairs fail closed on load with controlled errors.

Version 1 is migrated automatically: validate the entire schema and uniqueness,
decrypt every record using legacy AAD=None, then encrypt every record with v2 AAD
and fresh nonces before atomically replacing the file. IDs and timestamps are
preserved. Any validation, authentication or pre-replace write failure leaves the
original bytes intact; duplicate legacy pairs require manual resolution, never
an arbitrary first/last/latest choice. **V1 metadata that was tampered with before
migration cannot be cryptographically distinguished from legitimate legacy
metadata.** Migration binds the metadata present at migration time; it does not
retroactively authenticate history. Keep the original key for migration.

Saving an existing `(user_id, provider_id)` updates its secret, preserving its ID
and creation timestamp. The updated timestamp does not decrease. Metadata listing
and provider retrieval therefore select the same unique record.

Writes use an exclusively created, randomly named temporary file in the destination
directory, flush/fsync, then atomic replacement. POSIX files (temporary and final)
have mode `0600`, independent of umask; existing v2 files are tightened on load.
Directory fsync is attempted on POSIX; unsupported directory sync emits only a
bounded warning after the committed replacement. Windows writes remain atomic,
but effective access permissions depend on Windows ACLs; POSIX mode-bit guarantees
are not claimed there. `credentials.enc` is explicitly gitignored at any depth;
temporary files retain the existing `*.tmp` ignore rule.

`OMNI_CREDENTIAL_STORE_PATH` and the relative default `credentials.enc` are
unchanged. Choosing a durable default directory and coordinating concurrent writers
remain follow-ups. No process locking or key rotation is introduced here.

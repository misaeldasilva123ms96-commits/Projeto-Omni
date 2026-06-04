# Secrets Policy

Omni must never commit, log, persist, or expose secret values through public runtime payloads, frontend debug panels, learning records, tests, or documentation.

## Repository Rules

- Keep real credentials out of git.
- Use `.env` locally only.
- Keep `.env.example` limited to placeholders such as `<OPENAI_API_KEY>` and `<SUPABASE_URL>`.
- Do not use real-looking placeholders such as `sk-...`, `eyJ...`, `Bearer ...`, `ghp_...`, or `xoxb-...`.

## Encrypted Credential Store (P5D)

All provider secrets persisted to disk MUST be encrypted using AES-256-GCM authenticated encryption.

### Encryption Rules

- Never store API keys in plaintext on disk or in memory caches.
- Use `CredentialStore` from `config.encrypted_credential_store` for all credential persistence.
- Encryption key is loaded from `OMNI_CREDENTIAL_STORE_KEY` environment variable (64 hex chars = 32 bytes / 256 bits).
- Generate keys using: `python -c "import secrets; print(secrets.token_hex(32))"`
- Key validation occurs at startup — the store refuses to operate with an invalid key.
- Each encryption operation uses a unique 12-byte nonce (IV) generated via `os.urandom()`.
- Authentication tags are verified on every decryption — tampered data raises `TamperDetectedError`.

### Operational Rules

- `saveCredential()` — encrypts the secret before writing to the store file.
- `getCredential()` — returns decrypted value only when `decrypt=True` is explicitly passed.
- `getDecryptedSecret()` — explicit method for requesting plaintext; log the access event but never the value.
- `updateCredential()` — re-encrypts with a fresh nonce on every update.
- `deleteCredential()` — removes the entry from the store.
- `listCredentialMetadata()` — returns only metadata (id, user, provider, timestamps); never encrypted payloads.
- `verifyProviderMismatch()` — validates provider identity before credential use.

### Logging Rules

- Log operations (`Saved credential`, `Updated credential`, `Deleted credential`) with the credential ID only.
- Never log secret values, decrypted secrets, or encryption keys.
- User IDs are redacted in logs (first 2 chars + `***` + last char).

## Diagnostics Rules

Runtime diagnostics may expose only status booleans, public provider names, public error codes, and public messages.

Allowed Supabase diagnostic shape:

```json
{
  "supabase_configured": true,
  "url_present": true,
  "anon_key_present": true,
  "service_role_present": false
}
```

Allowed provider diagnostic fields include public names and booleans such as:

```json
{
  "provider": "openai",
  "configured": true,
  "key_present": true,
  "model_configured": true
}
```

Diagnostics must not include key values, key prefixes, key lengths, key hashes, raw config, raw environment, tokens, passwords, authorization headers, raw provider payloads, raw tool payloads, or memory content.

## Supabase Public Key Nuance

Browser Supabase anon keys can be intentionally public in frontend builds when protected by row-level security. Omni still treats Supabase config as non-diagnostic data: frontend runtime/debug panels must not echo raw Supabase URLs or keys.

Service-role keys are server-only secrets and must never be exposed to frontend code, runtime payloads, logs, docs, learning records, or tests.

## Provider Keys

Provider API keys are execution-only secrets. Internal code may read them from environment through controlled helpers, but public/debug/log paths may receive only booleans such as `configured` or `key_present`.

## Logs And Learning Records

Learning records and runtime logs must be redacted before persistence. Raw prompts, metadata, provider/tool responses, memory content, paths, and config payloads must pass through redaction helpers before writing to disk.

## If A Secret Leaks

1. Revoke or rotate the key immediately.
2. Remove the value from current code/docs/config.
3. Audit git history and deployment logs.
4. Add or update a regression test for the leak class.
5. Re-deploy with rotated credentials.

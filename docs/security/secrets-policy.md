# Secrets Policy

Omni must never commit, log, persist, or expose secret values through public runtime payloads, frontend debug panels, learning records, tests, or documentation.

## Repository Rules

- Keep real credentials out of git.
- Use `.env` locally only.
- Keep `.env.example` limited to placeholders such as `<OPENAI_API_KEY>` and `<SUPABASE_URL>`.
- Do not use real-looking placeholders such as `sk-...`, `eyJ...`, `Bearer ...`, `ghp_...`, or `xoxb-...`.

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

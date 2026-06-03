# Omni Access Layer: Real Puter Manual Smoke Runbook

This runbook is for local development validation of the experimental Free Mode
Puter browser path through `/dev/puter`. It does not connect Puter to production
chat, does not make Puter a default provider, and does not enable any production
Access Layer behavior.

## Preconditions

- Use a local development browser session only.
- Keep `/dev/puter` disabled by default.
- Do not commit local environment files.
- Do not add API keys or provider credentials. Puter browser testing does not
  require a server-side key in this phase.
- Do not enable BYOK storage, billing, Pro behavior, tools, files, function
  calling, or long memory.
- Do not use the main chat flow for this smoke test.

The route is available only when both flags are explicitly enabled:

```env
VITE_OMNI_EXPERIMENTAL_PUTER_FREE=true
VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=true
```

`frontend/.env.local` must remain local and untracked.

## Local Setup

1. From the repository root, create or update `frontend/.env.local`:

   ```env
   VITE_OMNI_EXPERIMENTAL_PUTER_FREE=true
   VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=true
   ```

2. Confirm the file is not tracked or staged:

   ```powershell
   git status --short
   git status --short --ignored frontend/.env.local
   ```

   Expected: `.env.local` may appear as ignored, but it must not appear as a
   tracked or staged file.

3. Start the frontend:

   ```powershell
   cd frontend
   npm run dev
   ```

4. Open the dev route in a browser:

   ```text
   http://127.0.0.1:5173/dev/puter
   ```

## Smoke Test Checklist

1. With both flags disabled, confirm `/dev/puter` does not expose the Puter
   manual surface.
2. With both flags enabled, confirm `/dev/puter` renders the development-only
   manual surface.
3. Confirm page load does not trigger a Puter call.
4. Confirm route load does not trigger a Puter call.
5. Confirm a manual button action is required before the harness can attempt a
   browser Puter call.
6. Click the manual test button only after confirming this is a local dev
   session.
7. Record only the sanitized result shown by the page.
8. If the call is denied or fails, record only the safe public reason displayed
   by the page.

## Safety Verification

The page must not show any of the following:

- raw provider request
- raw provider response
- stack trace
- API key
- access token
- provider credential
- environment value
- provider config
- private endpoint
- billing detail
- debug internals
- tools, files, or function-calling payloads

If any of those appear, stop the smoke test and treat it as a blocker.

## Expected Behavior

- `/dev/puter` is local/dev only.
- The main chat flow is not involved.
- Puter is not the default provider.
- No automatic call happens on page load.
- Manual action is required.
- Access Layer gates still apply through the dev route, manual surface, browser
  adapter, and manual harness.
- Output remains sanitized and public-safe.
- Raw Puter responses are never shown.
- Errors are reduced to safe public reasons such as `puter_call_failed`,
  `puter_unavailable`, `routing_denied`, or `invalid_access_snapshot`.

## Rollback And Cleanup

1. Stop the frontend dev server.
2. Remove or reset `frontend/.env.local` if the flags should no longer be active
   locally.
3. Confirm no tracked files changed:

   ```powershell
   git status --short
   ```

4. Never commit `frontend/.env.local`.

This smoke runbook is documentation only. Production integration remains a
future phase.

# Omni Access Layer: Puter Dev Script Loader

Phase 7G adds a dev-only Puter.js script loader for the local `/dev/puter`
manual smoke flow. It exists only so local developers can load the browser
runtime before using the existing manual harness.

## Scope

- Loader module: `frontend/src/lib/puter/puterScriptLoader.ts`
- Fixed script source: `https://js.puter.com/v2/`
- Dev route only: `/dev/puter`
- Required flags:
  - `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=true`
  - `VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=true`

Both flags remain disabled by default in `.env.example`.

## Behavior

- The loader does not run on app import.
- The loader does not run on normal app load.
- The loader does not run on route render or mount by itself.
- A visible dev-only `Load Puter runtime` action is required.
- Loading the script does not call `puter.ai.chat`.
- The existing `Run manual Puter check` action remains separate and is still
  required for any manual AI call attempt.
- Duplicate Puter.js script tags are avoided.
- Loader failures return safe public statuses only:
  - `idle`
  - `loading`
  - `loaded`
  - `unavailable`
  - `failed`

## Safety Boundaries

- The script URL is fixed in code and is not user-controlled.
- Arbitrary script URLs are not accepted.
- No API keys, access tokens, credentials, provider config, private endpoints,
  billing fields, debug fields, tools, files, function-calling options, or raw
  provider payloads are accepted by the loader.
- Loader errors are reduced to safe reasons such as `feature_disabled`,
  `non_browser_runtime`, `script_load_failed`, or `script_load_timeout`.
- The main chat flow is not connected to Puter.
- Puter is not the default provider.
- BYOK storage, billing, Pro behavior, tools, files, and long memory remain out
  of scope.

Production integration remains a future phase.

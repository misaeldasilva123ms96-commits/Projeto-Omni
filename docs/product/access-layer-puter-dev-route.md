# Omni Access Layer: Puter Dev Route

Phase 7E adds a guarded development route for the experimental Free Mode Puter manual surface. The route is intended for local browser validation only and is disabled by default.

## Route

- Path: `/dev/puter`
- Requires `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=true`.
- Requires `VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=true`.
- When either flag is disabled, the dev route does not resolve to the Puter surface.

## Safety Boundaries

- The route mounts the existing `PuterDevManualSurface`.
- No Puter call happens on import, render, mount, route load, or app load.
- A manual button action is still required.
- The manual harness still requires safe AccessSnapshotBoundary-style state, Free mode, `experimental_free_provider`, browser runtime, and Puter availability.
- Output remains sanitized and public-safe.

## Non-Goals

- No main chat flow integration.
- No default Puter provider behavior.
- No automatic provider or network calls.
- No tools, files, function-calling, or long memory in Free mode.
- No BYOK storage, billing, Pro behavior, or production brain behavior changes.
- No raw request, raw response, stack trace, environment value, provider credential, provider config, private endpoint, billing detail, or debug payload exposure.

Production user flow remains future work. Main promotion and any production route decisions remain manual owner-controlled steps.

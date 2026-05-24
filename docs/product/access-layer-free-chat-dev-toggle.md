# Omni Access Layer: Free Chat Dev Toggle

Phase 7M adds a dev-only chat-adjacent toggle surface for manually exercising
the Phase 7L dev-real Free chat bridge. It is mounted only inside the existing
`/dev/puter` development route and is not part of the normal chat user flow.

## Scope

- Surface: `frontend/src/lib/puter/PuterFreeChatDevToggleSurface.tsx`
- Mount: existing `/dev/puter` route
- Bridge dependency: `frontend/src/lib/puter/freeModeChatBridgeDevReal.ts`
- UI flag: `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false`

All related flags remain disabled by default:

- `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_BRIDGE_DEV_REAL=false`
- `VITE_OMNI_EXPERIMENTAL_PUTER_CHAT_DEV_TOGGLE=false`

## Behavior

The toggle does not render unless every required flag is explicitly enabled. It
does not run on import, render, mount, route load, or app load. A manual button
click is required before the Phase 7L bridge can be invoked.

The surface does not replace the normal chat provider, does not modify
`sendOmniMessage`, and does not connect Puter to the production chat flow. The
only real provider path remains the Phase 7L bridge, which itself delegates to
the existing gated manual harness after the Access Layer contract allows it.

If Puter displays a consent or auth prompt and the provider call remains
unresolved, the dev toggle reports a safe public state such as
`provider_consent_or_auth_pending`. The toggle must not auto-click, auto-accept,
hide, or bypass Puter consent/auth UI.

## Required Gates

The toggle and bridge require:

- Free plan only
- Free Puter feature flag enabled
- chat bridge feature flag enabled
- dev-real bridge feature flag enabled
- dev toggle feature flag enabled
- safe AccessSnapshotBoundary-style state
- quota allowed
- routing allowed
- selected provider family `experimental_free_provider`
- browser runtime and Puter runtime available
- no tools, files, function-calling, long memory, or sensitive tools
- no provider overrides, quota overrides, credentials, provider config, private
  endpoints, billing fields, or debug fields

## Safety

The visible output is sanitized text or a stable public-safe denial reason only.
The surface must not expose raw provider output, raw requests, stack traces,
credentials, API keys, access tokens, environment values, provider config,
private endpoints, billing data, or debug data.

This phase does not add BYOK storage, billing, Pro behavior, files, tools, or
long memory.

## Future Path

Next phase:

- Phase 7N: Controlled Free Chat Pilot Contract

That phase should remain contract-first and continue to avoid default provider
changes until explicitly promoted.

# Omni Access Layer: Real Puter Smoke Result

Phase 7H records the local development smoke result for the dev-only Puter
runtime loader and manual harness after Phase 7G.

## Validation Context

- Date: 2026-05-23
- Route tested: `/dev/puter`
- Required local flags:
  - `VITE_OMNI_EXPERIMENTAL_PUTER_FREE=true`
  - `VITE_OMNI_EXPERIMENTAL_PUTER_DEV_SURFACE=true`
- Local config source: ignored `frontend/.env.local`
- Scope: local/dev validation only

This result does not connect Puter to production chat, does not make Puter the
default provider, and does not enable Puter by default.

## Observed Loader Behavior

- `/dev/puter` was reachable when both dev flags were enabled.
- Initial state was safe:
  - loader status: `idle`
  - manual result: `not_invoked`
- No Puter script tag was present on page load.
- No automatic Puter or network call happened on page load.
- The visible `Load Puter runtime` action injected exactly one script:
  - `https://js.puter.com/v2/`
- The script source was fixed in code and was not user-controlled.
- Loader status became `loaded`.
- No duplicate Puter script tag was created.
- Loading the runtime did not call `puter.ai.chat`.

## Observed Manual Call Behavior

- `Run manual Puter check` remained a separate manual action.
- The manual check was attempted exactly once with a safe prompt.
- No files, tools, function-calling, long memory, BYOK key storage, billing, or
  Pro behavior were enabled.
- No login or auth prompt appeared during the observed run.
- The visible sanitized result was `ok`.
- The requested marker text was not displayed because the dev surface exposes
  only sanitized public-safe output.

## Security Observations

The validation did not show any of the following in the UI output:

- raw provider payload
- stack trace
- API key
- token
- environment variable
- credential
- provider config
- private endpoint
- billing data
- debug data

The main chat flow remained untouched. The Puter runtime loader and manual
harness stayed isolated to the dev-only `/dev/puter` flow behind explicit flags.

## Limitations

- This was a local development smoke validation, not a production integration.
- The result confirms that the dev-only loader can make the Puter runtime
  available for the manual harness under the tested local conditions.
- The result does not prove production readiness, billing behavior, quota
  persistence, provider routing execution, or chat-flow integration.
- Raw Puter responses were not stored or documented.

## Why Production Chat Is Still Unchanged

The validated path is still separate from the normal Omni chat path:

- `/dev/puter` is gated by explicit local dev flags.
- The runtime loader requires a visible manual action.
- The manual Puter check requires a separate visible manual action.
- Puter is not the default provider.
- No production chat send path is wired to Puter.
- Access Layer gates remain the intended control boundary for future work.

## Recommended Next Phase

Phase 7I: Controlled Free Chat Bridge Design, docs/contract first.

That phase should describe how a future Free-mode chat bridge would preserve
PlanPolicy, TokenQuota, ProviderRouter, ProviderRegistry, PublicAccessSnapshot,
AccessSnapshotBoundary, PuterClientAdapter, the browser skeleton, the manual
harness, and the dev route boundaries before any production chat integration is
implemented.

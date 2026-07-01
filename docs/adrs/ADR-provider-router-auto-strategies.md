# ADR: Provider Router Auto Strategies

Status: Proposed

Date: 2026-07-01

## Context

Projeto Omni already has Provider Center, BYOK, runtime truth, governance, tokens, fallback, observability and cockpit. The external OmniRoute repository was reviewed read-only as an architectural reference for provider routing and fallback.

OmniRoute shows useful patterns: `auto/*` routing profiles, weighted candidate scoring, last-known-good path, cost/quota/latency/health signals, circuit breakers, connection cooldowns, model lockouts and route explanation. It also includes features that must not enter Omni, including MITM, TLS stealth, proxy bypass, credential import flows and endpoint behaviors that may depend on non-official surfaces.

## Decision

Adopt the architectural pattern of policy-driven automatic provider routing, but implement it natively inside Omni using only Omni-governed provider contracts.

The Omni provider router should introduce:

- a `ProviderRouteCandidate` contract sourced from Provider Center/BYOK/runtime truth;
- `auto` strategy profiles such as balanced, coding, fast, low-cost and quota-aware;
- normalized scoring by health, quota, cost, latency, model capability, tenant policy and compliance eligibility;
- explicit fallback layers: provider breaker, connection cooldown and model lockout;
- route simulation/explanation before operator-facing activation;
- full runtime truth recording for selected and rejected candidates;
- cockpit views for route decision, fallback path, quota impact and cost estimate.

The router must not adopt:

- MITM or TLS interception;
- TLS fingerprint spoofing or stealth;
- proxy anti-detection or geo-bypass;
- web-cookie/session-token scraping;
- automated credential import from local tools;
- non-official provider endpoints;
- code copied from OmniRoute without license and compatibility review.

## Consequences

Benefits:

- Better provider resiliency without compromising compliance.
- Clear route explanations for cockpit and audit.
- Reuse of Omni runtime truth as the source of policy and evidence.
- Lower blast radius for provider/key/model failures.

Costs:

- Requires a first-class route candidate model and scoring tests.
- Requires careful calibration to avoid surprise provider changes.
- Needs policy controls for tenant, BYOK, budget and compliance.

Risks:

- Poor scoring could select cheaper but lower-quality models.
- Excessive fallback can hide provider incidents unless reported.
- Remote control via future MCP/A2A tools could mutate routing without adequate scopes.

## Guardrails

- Default to read-only simulation before automatic routing mutates behavior.
- Only official provider APIs and documented contracts are eligible.
- Every automatic decision must emit a redacted runtime-truth event.
- Tenant policy must be able to disable automatic provider switching.
- Fallback must not cross data residency, privacy, BYOK or compliance boundaries.
- Failure handling should fail-closed for auth/compliance and fail-open only for non-sensitive telemetry gaps.

## Open Questions

- Which initial strategies should be exposed in cockpit: `auto`, `auto/cost`, `auto/latency`, `auto/quota`, `auto/coding`?
- Should last-known-good path be scoped by tenant, user, session, workload type or provider group?
- What minimum evidence is required before enabling automatic routing for production tenants?

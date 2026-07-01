# Provider Auto Routing Foundation

Status: Draft implementation note

This document describes the first native Provider Auto Routing foundation for Projeto Omni.
It is based on Omni governance documents and uses OmniRoute only as an architectural reference.
No OmniRoute code, dependency, endpoint, credential flow, proxy flow, MITM flow, or TLS stealth behavior is copied or integrated.

## Scope

The foundation adds deterministic routing modes:

- `auto`
- `auto_fast`
- `auto_cheap`
- `auto_coding`
- `auto_safe`

The first scoring pass uses only internal, safe signals already available to Omni:

- provider registration and adapter status;
- model configuration;
- executable and available status;
- BYOK session compatibility;
- static internal cost, latency, coding, and safety hints;
- policy/governance allow or block result when provided by the caller.

The router fails closed when BYOK requires a provider that is not executable, policy blocks routing, or no valid candidate exists.

## Runtime Truth

When automatic routing is active, runtime truth includes a public-safe `provider_auto_routing` block:

- `routing_mode`
- `selected_provider`
- `selected_model`
- `candidate_count`
- `decision_reason`
- `fallback_used`
- `rejected_candidates`
- `rejected_reasons`
- `fail_closed_reason`
- `policy_result`
- `created_at`

This block is allowlisted and sanitized before it is attached to public runtime truth. It must not include API keys, headers, request bodies, raw provider payloads, logs, stack traces, proxy settings, endpoint overrides, or imported credentials.

## Out Of Scope

This foundation does not implement:

- token compression pipeline;
- MCP or A2A routing;
- dashboard or advanced cockpit views;
- provider credential import;
- provider scraping;
- unofficial provider endpoints;
- proxy, bypass, MITM, or TLS stealth behavior;
- provider-control bypass;
- automatic merge or direct changes to `main`.

Frontend presentation of the new runtime truth block is deferred until the Runtime Inspector has a stable public UI contract for provider auto-routing fields.

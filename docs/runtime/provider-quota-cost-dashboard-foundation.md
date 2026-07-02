# Provider Quota & Cost Dashboard Foundation

## Summary

This foundation adds a small, governed provider quota and cost view to the Runtime Inspector. It uses only internal runtime metadata, provider diagnostics and already-sanitized runtime truth. It does not call billing APIs, quota APIs, unofficial endpoints or external services.

OmniRoute is not integrated and no OmniRoute code was copied.

## Safe Contract

The internal provider usage summary contract is optional-field only:

- `provider`;
- `model`;
- `status`;
- `health`;
- `estimated_cost`;
- `quota_status`;
- `quota_remaining`;
- `quota_reset_at`;
- `last_latency_ms`;
- `last_error_reason`;
- `routing_mode`;
- `selected_by_auto_routing`;
- `fallback_count`;
- `updated_at`.

All string values are passed through the existing runtime debug redaction path before rendering. Unknown quota and cost values are shown as unavailable rather than inferred.

## Data Sources

Allowed sources for this phase:

- public runtime truth `provider_usage_summary`, when present;
- public runtime truth `provider_auto_routing`;
- existing provider diagnostics already used by the Runtime Inspector.

When explicit quota/cost data is absent, the UI derives only safe status indicators such as provider name, model, latency, auto-routing selection and fallback count. It does not calculate billing totals or query providers.

## Visual States

The Provider tab now supports compact states for:

- data available;
- partially available data;
- quota not configured;
- provider unavailable;
- sanitized error;
- no data.

## Security Guardrails

The dashboard must not render:

- API keys;
- headers;
- env vars;
- tokens;
- cookies;
- raw provider payloads;
- raw billing payloads;
- stack traces;
- unredacted error text.

## Out Of Scope

This foundation does not implement:

- real billing;
- external billing integration;
- quota scraping;
- private or unofficial endpoints;
- definitive financial calculations;
- automatic provider import;
- MCP/A2A;
- token compression changes;
- provider router changes;
- proxy, MITM, TLS stealth or bypass flows;
- OmniRoute integration.

## Merge Policy

This is a dashboard foundation only. Merge remains manual by Misael after review and CI.

# External API Gateway foundation

Phase 1 establishes the governed boundary for future **outbound** API access. It
does not add an HTTP client, register a provider, or activate internet access.
The Omni inbound API exposed to users is a separate boundary from outbound APIs
that the Python Brain may use in later phases.

```text
User
 ↓
Rust
 ↓
Python Brain
 ↓
OmniRoute
 ↓
Tool Selection
 ↓
Execution Manifest
 ↓
External API Registry
 ↓
External API Policy
 ↓
[Future External API Gateway]
 ↓
Internet
```

## Security model

External APIs are deny-by-default. `OMNI_EXTERNAL_API_ENABLED` defaults to
`false`; a registered API remains non-executable while that gate is off. The
registry is explicit, starts empty, rejects duplicate or invalid definitions,
and performs no discovery. A model-produced API ID, endpoint, or tool name does
not register anything and does not gain authority through an Execution Manifest.

Policy requires HTTPS, an explicitly allow-listed host and method, no embedded
URL credentials, and a registered, enabled API with a known authentication type.
Literal localhost, loopback, private, link-local, reserved, unspecified, and
multicast IP targets are denied. Redirect behavior and response limits are part
of each declaration for the future gateway to enforce.

These checks are not complete SSRF protection. The future HTTP transport must
resolve DNS itself, validate every resolved IP before connecting, pin or
revalidate the destination across redirects, and defend against DNS rebinding.

## Trust and provenance

The future `public-apis/public-apis` catalog is candidate discovery input, not a
trust root. Future OpenAPI documents likewise must never cause automatic
registration or execution. Maintainer review, explicit registry configuration,
the global feature gate, policy evaluation, and gateway enforcement are all
separate requirements.

Response provenance is prepared for source type, provider, API ID, retrieval
time, endpoint, cache state, freshness, and request ID. API keys, Authorization
headers, cookies, tokens, and sensitive payloads must never enter provenance,
observability records, prompts, or model context. Secrets must remain inside the
future gateway's credential boundary.

## Phase 1 status

No external API is registered or active. HTTP transport, retries, provider
routing, DNS/IP post-resolution validation, credential injection, caching, and
real provider integrations are deferred to later reviewed phases.

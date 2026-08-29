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
External API Gateway
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

The Phase 2 transport resolves A/AAAA records itself and denies the request if
any returned address is not globally routable. It connects to one address from
that validated set without a second DNS lookup. The logical hostname is retained
for the HTTP `Host` header, TLS SNI, hostname verification, and certificate
validation. TLS verification cannot be disabled through the Gateway API.

Requests contain `api_id + governed path + structured query`; callers cannot
supply an absolute URL. Provider definitions control the scheme, host, method,
timeout, streaming response limit, redirect mode, retry count, cache TTL, and
local rate limit. Open-Meteo denies every redirect. The transport never follows
`Location`, so cross-host redirects and HTTPS-to-HTTP downgrades cannot execute.

## Transport controls

- Timeouts apply to connect and response I/O and return `request_timeout`.
- Responses are read in bounded chunks and aborted immediately above the
  provider's byte ceiling.
- JSON decoding happens only after the bounded read; malformed JSON is rejected.
- GET may retry connection failures, timeouts, 429, 502, 503, and 504, with at
  most the registry's small attempt count and injected/testable backoff.
- Validation, policy denials, redirects, ordinary 4xx, and schema failures do
  not retry.
- The in-memory TTL cache has bounded capacity and a deterministic request key.
  Headers, credentials, and cookies never enter the key or cached value.
- A thread-safe, per-process token window limits provider calls. Open-Meteo is
  capped at 30 provider requests per minute per process, far below its published
  free-tier ceiling. Cache hits do not consume provider quota.

The controls are process-local. Horizontal deployments need a separately
reviewed distributed quota design before commercial production.

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

## Open-Meteo pilot

`weather_forecast` is an explicitly registered and governed external read. It
accepts only latitude (`-90..90`), longitude (`-180..180`), and 1–7 forecast
days. The adapter always calls `GET /v1/forecast` with a fixed set of current
and daily variables and `timezone=auto`; it cannot accept arbitrary provider
fields or hosts. Provider JSON is type-checked and reduced to location,
timezone, current conditions, daily forecast, provider, and provenance.

Both gates default off and must be true:

```text
OMNI_EXTERNAL_API_ENABLED=false
OMNI_EXTERNAL_OPEN_METEO_ENABLED=false
```

The registry entry must also be enabled and policy-approved. There is no city
lookup or geocoding in Phase 2.

The free endpoint is classified solely as a development/evaluation,
non-commercial pilot. Open-Meteo requires attribution and publishes its free
data under CC BY 4.0 conditions. Commercial production requires a new licensing
and provider-plan review. Provenance retains a short `Weather data by
Open-Meteo.com` attribution.

## Observability and privacy

The Gateway emits `external_api.request_started`, `policy_denied`, `cache_hit`,
`request_succeeded`, `request_failed`, and `rate_limited`. Payloads contain only
bounded API ID, method, outcome, cache state, or reason. URLs, query strings,
headers, and coordinates are omitted. General execution receipts replace weather
coordinates with `coordinates=redacted`; coordinates remain only in the
governed request and requested normalized result.

Runtime Truth marks actual executions with source `external_api`, provider
`open_meteo`, tool `weather_forecast`, and cache state.

## Threat model and remaining boundaries

Mitigated in Phase 2: model-selected hosts, literal and post-DNS SSRF, mixed
public/private DNS answers, DNS rebinding between validation and connect,
invalid TLS, automatic redirects, unbounded downloads, infinite retries,
unbounded cache growth, and ungoverned provider volume.

Residual risks include provider compromise, malicious-but-valid public DNS
destinations after an approved domain is compromised, per-process rather than
distributed quotas, process-local cache, and coarse coordinate privacy in the
requested result. Proxy support, secret injection, custom certificate stores,
and SAME_HOST redirects are intentionally absent.

## Phase 2 status

Open-Meteo is the only registered provider and remains disabled unless both
feature gates are explicitly enabled. The main test suite uses fake DNS and
transport boundaries and never requires internet access. Live smoke testing is
opt-in only through `OMNI_EXTERNAL_LIVE_TESTS=1`.

## Nominatim settlement-geocoding pilot

Phase 3 adds `geocode_place` through the same registry, policy, DNS validation,
pinned TLS transport, response limits, cache, rate limiter, provenance, and
governed execution path. The only registered Nominatim endpoint is HTTPS
`nominatim.openstreetmap.org/search`, GET only, with redirects denied. The tool
accepts a bounded place/municipality name, optional state or region, and an
optional ISO 3166-1 alpha-2 country code. It cannot select provider parameters,
hosts, residential-address fields, reverse lookup, autocomplete, or POI search.

The public instance is an opt-in development/evaluation pilot, not a generic
geocoding backend for unrestricted Omni traffic. Both gates default off:

```text
OMNI_EXTERNAL_API_ENABLED=false
OMNI_EXTERNAL_NOMINATIM_ENABLED=false
```

The adapter sends an identifiable, project-specific User-Agent, requests only
`jsonv2`, address details, at most three settlement candidates, and fixed
languages. It makes one attempt, enforces a local window of one request per 1.1
seconds, and caches normalized-equivalent searches for 24 hours. Cache and rate
state are per process, so the public pilot is unsuitable for horizontal
multi-instance production.

Provider results are schema-checked, bounded to three candidates, and reduced to
display name, coordinates, country code, category, type, importance, and optional
region. One result is marked `unique`; multiple results are preserved as
`ambiguous` rather than silently choosing the first. No coordinates are invented.
The runtime does not currently expose typed output binding from one tool into the
arguments of another, so geocode-to-weather composition remains deferred instead
of parsing model text or creating a bypass.

General events omit the raw place query, full coordinates, request headers, and
User-Agent. The execution intent records only a redacted place query and whether
a country filter was supplied. Provenance strips query strings and retains short
Nominatim/OpenStreetMap attribution.

The usage policy, Search API, and OpenStreetMap attribution guidance were reviewed
on 2026-08-29. Operational constraints and source links are recorded in
`docs/integrations/nominatim.md`.

## Typed geocode-to-weather composition

Phase 4 adds a runtime binding layer above provider adapters. A unique normalized
Nominatim candidate may supply only finite latitude and longitude to a subsequent
Open-Meteo action identified by step ID. The binding does not alter Gateway
requests, cache keys, provider rate limits, retries, gates, provenance, or the
normalized weather schema. Ambiguous or failed geocoding prevents weather
transport. See `docs/architecture/tool-output-bindings.md`.
# Phase 5: currency, dictionary, and closed safe paths

Frankfurter v2 and Free Dictionary share the existing gateway, DNS pinning, TLS,
redirect denial, byte limits, cache, rate limiter, observability, and provenance.
Frankfurter retains an exact fixed path. Free Dictionary adds only the
`FREE_DICTIONARY_ENGLISH_WORD` closed template; there is no prefix, glob, caller
regex, wildcard, or general URL-template authority. The adapter validates one
segment before encoding and policy independently checks the constructed path.

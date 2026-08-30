# Nominatim public-instance pilot

Policy reviewed: 2026-08-29.

This integration is an explicit, opt-in development/evaluation pilot for bounded
settlement lookup. It is not a generic geocoding, address lookup, place search,
autocomplete, POI, or map-search service. Do not send personal data, confidential
material, residential addresses, or person-associated coordinates.

## Official sources and obligations

- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)
  sets an absolute maximum of one request per second, requires an identifying
  User-Agent or Referer, requires attribution and client-side caching, prohibits
  heavy use and autocomplete, and limits bulk operation. It also restricts use by
  LLM/no-code/low-code platforms as a generic geocoding facility.
- [Nominatim Search API](https://nominatim.org/release-docs/latest/api/Search/)
  documents `/search`, `jsonv2`, `countrycodes`, `accept-language`, and
  `featureType=settlement`. Settlement filtering covers inhabited address-layer
  features and avoids opening the query to generic POIs.
- [OpenStreetMap copyright and licence](https://www.openstreetmap.org/copyright)
  requires OpenStreetMap attribution and notice that data is available under the
  Open Database Licence.

The provider declaration uses a process-local safety throttle of one request per
1.1 seconds, one attempt, a 24-hour cache,
at most three candidates, and only one request thread initiated per governed tool
execution. Repeated normalized queries are served from cache without transport.

The identifying header is stable and public:

```text
Projeto-Omni-Geocoder/1.0 (+https://github.com/misaeldasilva123ms96-commits/Projeto-Omni)
```

It contains no personal email, token, key, session ID, or user data.

## Production limitation

Cache and rate limiting are local to one Python process/instance. They are not a
distributed limiter or proof of application-wide compliance. The public pilot
also requires explicit compliance and single-instance operator acknowledgements,
`OMNI_PYTHON_MODE=service`, and
`OMNI_PYTHON_SERVICE_FALLBACK_TO_SUBPROCESS=false`. Missing or invalid values
fail closed before cache, DNS, or transport. Omni cannot technically prove that
other replicas or workers do not exist; the maintainer assumes that operational
responsibility when enabling the pilot. These acknowledgements prevent accidental
activation but do not prove compliance or topology.

The public Nominatim pilot is therefore not suitable for horizontally scaled or
unrestricted production use.
Before production or increased traffic, replace it with a reviewed self-hosted
Nominatim deployment, a suitable commercial provider, or another provider behind
the same External API Gateway. Policy can change without notice and must be
reviewed again before deployment.

The public service must not be used for autocomplete, systematic/bulk queries,
or as a generic geocoding/search service. Repeated queries should be served from
cache. Use in an LLM-assisted development context requires deliberate maintainer
review, and the public policy or availability may change or be withdrawn.

Attribution retained in provenance:

```text
Geocoding by Nominatim; data © OpenStreetMap contributors, ODbL 1.0
```

When used by the typed geocode-to-weather flow, only a unique candidate's
validated latitude and longitude cross the internal binding boundary. The model
does not copy coordinates, ambiguous candidates are never auto-selected, and the
binding does not cause retries or bypass this provider's cache, quota, or gates.

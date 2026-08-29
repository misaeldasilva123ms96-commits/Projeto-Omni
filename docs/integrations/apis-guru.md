# APIs.guru discovery catalog

The official REST API (v2.2.x documentation reviewed 2026-08-29) is the recommended interface for
the community-driven public OpenAPI directory. Omni uses only `GET /v2/list.json` on
`api.apis.guru`; it does not use raw Git repository content.
The source permits 2 outbound transport attempts per minute/process and at most 2 attempts per
load; each attempt consumes quota.

The current `ApiVersion` contract exposes `openapiVer`, `swaggerUrl`, and `externalDocs` at the
version level. Omni preserves `openapiVer` exactly as an unverified catalog hint and reads the
version-level documentation URL (with a defensive legacy `info.externalDocs` fallback only when
the current field is absent). `swaggerUrl` is the historical field name for the JSON OpenAPI
document URL. A locator is retained only for the closed `swagger.json` / `openapi.json` filename
set under the official authority; this does not authorize or perform a schema fetch.

Phase 8 can fetch one selected mirrored JSON schema only after five opt-in gates and independent
candidate identity/authority/path validation. The candidate-scoped registry authorizes that exact
path only. All references, servers, external documentation, OAuth/OpenID URLs, callbacks, and
webhooks found in the document remain non-network metadata and require human review.

Only each API record's preferred version becomes a Phase 7 candidate. A future schema locator is
retained only when it is credential-free HTTPS on `api.apis.guru`, begins `/v2/specs/`, ends
`/swagger.json`, and has no fragment. No spec, origin, external documentation, registration URL,
or logo is fetched. The catalog is not a trust root.

APIs.guru catalog/definition licensing and fair-use metadata do not grant permission to use an
underlying API. Provider-specific terms always require human review.

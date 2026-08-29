# APIs.guru discovery catalog

The official REST API (v2.2.x documentation reviewed 2026-08-29) is the recommended interface for
the community-driven public OpenAPI directory. Omni uses only `GET /v2/list.json` on
`api.apis.guru`; it does not use raw Git repository content.

Only each API record's preferred version becomes a Phase 7 candidate. A future schema locator is
retained only when it is credential-free HTTPS on `api.apis.guru`, begins `/v2/specs/`, ends
`/swagger.json`, and has no fragment. No spec, origin, external documentation, registration URL,
or logo is fetched. The catalog is not a trust root.

APIs.guru catalog/definition licensing and fair-use metadata do not grant permission to use an
underlying API. Provider-specific terms always require human review.

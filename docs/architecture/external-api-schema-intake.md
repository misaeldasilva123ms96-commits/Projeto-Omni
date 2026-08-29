# Governed OpenAPI schema intake

Phase 8 adds a maintenance-only boundary between a reviewed discovery candidate and a provider
design proposal. It does not register a provider, generate code, credentials, or tools, grant
network authority, or execute an API operation.

## Exact network authority

Only an unpromoted `apis_guru` candidate with a valid deterministic identity and an available
candidate-bound schema locator is supported. Intake revalidates scheme, host, port, path,
credentials, query, fragment, controls, traversal, percent-encoded separator ambiguity, provider,
service, and preferred version. It then creates an ephemeral registry containing exactly one `GET`
path on `api.apis.guru`. The definition is bounded to 8 MiB, one attempt, one request/minute, no
redirect, and no cache. All five feature gates default off and are checked before DNS.

## Structural inspection

The analyzer supports Swagger 2.0 and OpenAPI 3.0.x, 3.1.x, and 3.2.x as structural metadata, not
as a full conformance validator. Iterative traversal caps nodes, depth, paths, operations,
references, security schemes, servers, and tags. It records methods, parameters, media types,
responses, security declarations, servers, callbacks, webhooks, uploads, and objective risk
signals. OAS 3.2 `QUERY` and `additionalOperations` are metadata only and do not extend the runtime
gateway.

Internal references are counted but not resolved. External and relative-document `$ref` values are
recorded but never followed, so reference cycles are never traversed. Servers are never contacted;
externalDocs, examples with `externalValue`, OAuth/OpenID URLs, link operation references,
callbacks, and webhooks are never fetched or executed. Untrusted descriptions are normalized as
bounded plain text and the raw schema is never sent to an LLM.

## Review-only proposal

The canonical JSON representation produces a SHA-256 fingerprint and byte count; neither is
claimed to be a raw-response digest or Content-Length. The deterministic frozen
`ProviderDesignProposal` summarizes the structure and always requires maintainer, terms, security,
privacy, cost, rate-limit, and provider-documentation review. Execution, registration, code
generation, credential generation, and network authority remain false. Server declarations and
security schemes never modify provider allowlists, credential configuration, tools, manifests, or
execution registries.

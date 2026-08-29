# External API discovery control plane

Phase 7 separates discovery, registration, and execution. External catalogs are untrusted
candidate sources, not security authorities. A `DiscoveryCandidate` cannot register a provider,
execute a request, become a tool, or grant network authority. Every candidate is imposed by Omni
as `discovery_only`, `manual_review_required`, `execution_authorized=false`,
`registration_authorized=false`, and `network_authority=false`.

## Flow and isolation

The maintenance-only flow is: governed source fetch, bounded deterministic parser, normalized
candidate, local text search, and human-review dossier. `build_discovery_source_registry()` owns
only `discovery_apis_guru` and `discovery_public_apis`. The executable
`build_external_api_registry()` and `EXTERNAL_TOOLS` remain unchanged. There is no public HTTP
endpoint and no agent/planner/manifest tool surface for discovery.

Network loading fails closed unless all three gates are true: `OMNI_EXTERNAL_API_ENABLED`,
`OMNI_EXTERNAL_DISCOVERY_ENABLED`, and the selected source gate. Both catalogs cache independently
for 24 hours. APIs.guru is limited to 2 requests/minute/process and public-apis to 1. Redirects are
denied. Search and dossier generation are entirely local after loading.

The only authorized requests are `GET https://api.apis.guru/v2/list.json` and `GET
https://api.github.com/repos/public-apis/public-apis/contents/README.md?ref=master`. Catalog
documentation links, origins, logos, `download_url`, and OpenAPI locators are display-only
metadata and are never resolved or fetched. The APIs.guru catalog cap is 16 MiB; the GitHub JSON
envelope is capped at 4 MiB and decoded README at 2 MiB. These bounds comfortably exceed the
catalogs reviewed on 2026-08-29 while remaining finite.
The live review normalized 2,529 APIs.guru records and 1,622 public-apis records; the latter came
from GitHub blob `e762d6a46162729fe7fed004f6b914b99c5968bf`.

## Trust and review boundary

Catalog text is Unicode-normalized, stripped of control characters, flattened to plain text, and
bounded before storage. Parsing uses no LLM. Ranking is deterministic text relevance only, never
trust, safety, quality, or production readiness. Cross-source records remain separate.

A dossier always requires terms, security, privacy, and implementation review. Human review must
consult official provider documentation and assess commercial terms, privacy, authentication,
rate limits, cost, sensitive data, endpoint scope, and security. Catalog metadata such as “HTTPS”,
“No auth”, or “free” is only what the catalog reports and may be stale.

## Threat model

Controls address catalog poisoning and prompt injection, malicious documentation URLs and schema
locators, SSRF through candidate URLs, automatic authority escalation, license/terms confusion,
oversized catalog denial of service, malformed base64/UTF-8, deterministic-ID collision risk,
stale metadata, and false HTTPS/auth claims. Invariant: any `evil.example` string inside a record
can neither reach DNS/transport nor modify a registry.

Safe discovery events contain only source, candidate count, cached state, and issue count. They do
not contain catalog bodies, descriptions, or URLs. Discovery is maintenance control-plane work and
does not claim tool execution or cognitive runtime truth.

## Maintenance CLI

`scripts/external_api_discovery.py` accepts only `--source`, `--query`, `--category`, `--limit`, and
`--format`. It prints bounded review dossiers to stdout and has no install, register, execute, host,
URL, repository, branch, or file-writing option.

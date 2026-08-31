# Governed external API credentials

Reviewed 2026-08-29. Authenticated providers reference a stable maintainer-owned
credential ID; callers, planners, adapters, and requests cannot select an
environment variable or supply a secret. The production resolver maps the ID to a
server environment variable at execution time, validates it, and returns a trusted
header binding only inside `ExternalAPIGateway`.

Policy and global/provider gates run before credential resolution. Credentials are
validated before cache access, so an old cache entry cannot bypass missing or
invalid deployment credentials. Secrets are never cache-key inputs, payload data,
provenance, events, errors, manifests, runtime truth, or tool arguments. Trusted
auth injection occurs only for live transport; caller-sensitive headers are denied.

Environment reads occur per execution to permit rotation where the deployment
platform propagates changes; some platforms may still require a process restart.
This phase adds no secret database, UI, OAuth, or external secret manager.

## Threat model

- Credential leak/header injection: closed IDs/header names, validation, caller
  header denial, and transport-only injection.
- Secret in cache/logs: digest-only body cache identity and metadata-only events.
- Redirect leakage: authenticated provider redirects are denied.
- URL privacy/internal exfiltration: raw indicators are redacted; internal names
  and non-global IP literals are rejected before credentials/network.
- SSRF/malicious fetching: targets are never resolved or fetched; the sole network
  authority is the exact provider host through pinned TLS.
- Provider overclaiming: `not_listed` never means safe, benign, or trusted.

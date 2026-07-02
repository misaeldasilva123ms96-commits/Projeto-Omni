# Token Compression Foundation

## Summary

This document describes the first native Omni foundation for governed token compression. The implementation is intentionally small: it defines internal contracts, deterministic modes and safe runtime-truth metadata, without changing provider routing, frontend behavior, MCP/A2A, dashboards or external integrations.

OmniRoute was used only as an architectural reference through the approved ADRs. No OmniRoute code or dependency was copied.

## Modes

- `off`: default mode. Compression is skipped and the original content is returned to the caller.
- `lite`: collapses excessive blank lines and consecutive duplicate lines.
- `standard`: applies safe redaction, deduplicates repeated lines, and keeps a head/tail preview with an omission marker.
- `aggressive`: applies the strongest deterministic head/tail and duplicate-line reduction allowed in this foundation.

## Safe Payload Types

Compression is allowed only for explicit safe textual payload classes:

- long logs;
- test output;
- large diffs;
- repeated messages;
- long textual history.

Headers, credentials, env files, raw provider payloads and other sensitive payload classes are not safe payload types.

## Governance And Fail-Closed Rules

The pipeline is policy-governed and fail-closed when:

- policy result is not `allow`;
- payload type is not in the safe allow-list;
- content includes a secret indicator such as API keys, bearer tokens, provider key env vars, cookies or private keys;
- safe redaction fails;
- compression would reduce required auditability.

Secret-bearing content is not compressed. Public runtime truth records only sizes, strategy and reason fields.

## Runtime Truth Metadata

The runtime truth surface may include:

- `compression_mode`;
- `input_size`;
- `output_size`;
- `compression_ratio`;
- `strategy_used`;
- `redaction_applied`;
- `skipped_reason`;
- `fail_closed_reason`.

The runtime truth metadata must not include raw content, API keys, headers, env vars, tokens, stack traces or provider payloads.

## Out Of Scope

This foundation does not implement:

- semantic compression;
- summarization by LLM;
- embeddings;
- MCP/A2A compression;
- cost or quota dashboards;
- Runtime Inspector changes;
- direct OmniRoute integration;
- external compression dependencies;
- credential, header, env-var or raw-provider-payload compression.

## Audit Notes

The pipeline is opt-in by explicit internal call. It does not compress normal runtime messages automatically in this phase. This preserves runtime truth and auditability while giving future work a small governed contract to build on.

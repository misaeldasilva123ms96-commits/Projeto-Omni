# ADR: Token Compression Pipeline

Status: Proposed

Date: 2026-07-01

## Context

Projeto Omni needs token efficiency without weakening auditability, privacy or prompt integrity. The read-only OmniRoute review identified useful compression patterns: engine registry, pipeline modes, command-output filtering, MCP result compression, preview/compare APIs, fail-open behavior and response headers describing the applied compression plan.

The same review also surfaced risks: semantic compression can alter intent, retained raw output can expose secrets, optional ML dependencies can expand supply-chain risk, and aggressive compression may damage legal, security or debugging evidence.

## Decision

Design a native Omni token compression pipeline as an opt-in, policy-governed subsystem.

The pipeline should support:

- default mode `off`;
- named profiles such as `lite`, `tool-output`, `structured`, `semantic-safe` and `aggressive-experimental`;
- engine contract with stable id, config schema, validation, preview and measured stats;
- deterministic filters for shell/test/log/tool output before semantic compression;
- protection rules for code blocks, JSON, URLs, paths, stack traces, secrets, policy text and audit evidence;
- preview/compare endpoint before activation;
- runtime truth events for before/after token estimates, selected engines, skipped engines and reason;
- cockpit analytics for savings, failures, quality checks and policy blocks;
- explicit tenant/workload policy controlling when compression is allowed.

The pipeline must not:

- rewrite security/audit evidence by default;
- store raw unredacted payloads for recovery without retention and access policy;
- download or run optional ML models without SBOM, pinning and operator approval;
- compress across tenant boundaries;
- hide compression from route decision logs;
- treat token savings as more important than correctness or compliance.

## Consequences

Benefits:

- Lower token cost and larger effective context windows.
- Cleaner tool-output handling for cockpit and coding workflows.
- A measurable, reversible path for compression adoption.

Costs:

- Requires engine contracts, profile governance and quality tests.
- Adds observability and policy complexity.
- Needs careful redaction and data-retention design.

Risks:

- Semantic drift from lossy compression.
- Secret leakage through retained raw output or compression logs.
- Supply-chain exposure from optional compression engines.
- Debugging confusion if operators cannot see what was compressed.

## Guardrails

- `off` remains the default and must be available per request.
- Compression must be explainable in headers/events/cockpit.
- Engines fail-open to original content on engine failure, but fail-closed when policy/redaction validation fails.
- High-risk workloads require preview or explicit policy enablement.
- Compression output must pass integrity checks for protected structures.
- Raw-output recovery, if implemented, must be encrypted, redacted, access-controlled and retention-bound.

## Open Questions

- Which workloads can safely enable `tool-output` compression first?
- What minimum fidelity checks are required before semantic compression is allowed?
- Should compression profiles be tenant-level, workspace-level, route-level or per request?

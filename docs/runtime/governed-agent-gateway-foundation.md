# Governed Agent Gateway Foundation

## Summary

This document describes the first native Omni foundation for a governed agent gateway. The implementation is intentionally small: it evaluates internal agent capability requests, returns an allow or deny decision, and exposes safe runtime truth metadata. It prepares a future MCP/A2A layer without implementing MCP, A2A, remote agent execution, external servers, public endpoints or tool execution.

OmniRoute is not integrated and no OmniRoute code was copied.

## Internal Contract

The gateway evaluates an internal request with:

- `agent_id`;
- `agent_name`;
- `agent_type`;
- `requested_capability`;
- `allowed_capabilities`;
- `denied_capabilities`;
- `tool_scope`;
- `policy_result`;
- `decision`;
- `decision_reason`;
- `risk_level`;
- `created_at`.

The output is deterministic and metadata-only. It does not execute tools, open network connections, run shell commands, modify Git state, create files, call providers or import credentials.

## Safe Capability Allow-List

The initial safe capability list is:

- `read_safe`;
- `summarize`;
- `inspect_runtime`;
- `inspect_docs`;
- `propose_patch`;
- `create_report`.

`propose_patch` is allowed only as a proposal capability. It does not write files or apply patches in this foundation.

## Blocked Capabilities

The following capabilities are denied by default:

- `write`;
- `destructive`;
- `shell`;
- `network`;
- `git_sensitive`;
- `credential_access`;
- `provider_control`.

The foundation fails closed when policy blocks the request, when a sensitive capability is requested, when an unknown capability is requested, or when the request/context includes secret indicators.

## Runtime Truth Metadata

Public runtime truth may include a `governed_agent_gateway` block with only:

- `agent_id`;
- `agent_type`;
- `requested_capability`;
- `decision`;
- `decision_reason`;
- `denied_capabilities`;
- `risk_level`;
- `policy_result`;
- `created_at`.

The runtime truth block is allowlisted and sanitized before exposure.

## Security Boundary

The gateway must not expose:

- raw prompts;
- API keys;
- headers;
- env vars;
- tokens;
- cookies;
- raw payloads;
- stack traces;
- credential imports;
- provider-control payloads.

Requests with secret indicators are denied and only safe reason metadata is returned.

## Out Of Scope

This foundation does not implement:

- MCP server behavior;
- A2A protocol behavior;
- remote agent execution;
- agent marketplace behavior;
- dashboard expansion;
- real tool execution;
- shell or network execution;
- Git-sensitive execution;
- provider control;
- external endpoints;
- scraping;
- proxy, MITM, TLS stealth or bypass flows;
- direct OmniRoute integration.

## Audit Notes

This is an internal contract and runtime truth foundation only. Future MCP/A2A work must add separate governance review, public-boundary review, threat modeling, explicit policy gates, tests and manual PR review before any execution or protocol surface is enabled.

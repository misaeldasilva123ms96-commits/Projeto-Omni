# Static external API implementation plans

Phase 10 adds an offline design-analysis boundary. It consumes only a verified
`ProviderDesignProposal v2`, `HumanApprovalManifest v1`, and
`NonExecutableProviderScaffold v2`, fully revalidates that chain, fingerprints the
current runtime capability contract, and emits a content-bound
`StaticProviderImplementationPlan v2`.

An implementation plan is not implementation. It does not generate source code,
instantiate `ExternalAPIDefinition`, create credentials or feature gates, register
tools or providers, grant network authority, or activate runtime behavior. Every
authority field is structurally fixed to false.

## Artifact and runtime binding

The plan binds the scaffold, approval, proposal, candidate, canonical schema, full
proposal snapshot, and `external-api-runtime-capabilities-v1` fingerprint. The plan
ID is SHA-256 over canonical JSON for the complete plan excluding only the ID itself.
Internal verification detects unchanged-ID tampering; input verification rederives
the complete plan and detects even correctly rehashed tampering as stale.

The runtime profile records the current field names of `ExternalAPIRequest` and
`ExternalAPIDefinition`, plus the closed values of `AuthenticationType` and
`SafePathTemplate`. Contract drift changes its fingerprint. Meaningful capability
changes require a profile-version bump and freshly generated plans.

## Current runtime constraints

- Exact paths and existing maintainer-owned closed path templates are supported.
  Arbitrary OpenAPI templates are not converted into regexes, globs, or templates.
- Query values and form-urlencoded requests can be candidates after adapter and
  allowlist design. Arbitrary JSON bodies, multipart/file upload, cookies, and
  arbitrary provider headers are not treated as supported request authority.
- The gateway response contract is JSON. Non-JSON, binary, and streaming responses
  remain unsupported for generated plans.
- Generated plans require redirect denial and describe automatic retry capability
  only for GET. They make no retry assumption for other methods.
- Declared security-scheme compatibility is provider-level metadata. Header API
  keys are potentially compatible, query API keys, Basic, OAuth, and OpenID require
  runtime extensions, bearer requires maintainer design, and cookie API keys and
  mutual TLS are unsupported if a maintainer eventually selects those schemes.

Operation authentication compatibility is derived only from preserved operation and
root security semantics. Proposal v2 does not preserve exact scheme names, AND/OR
requirements, or scopes bound to an operation. An operation inheriting absent global
security is therefore only potentially compatible and requires revalidation. An
operation inheriting present global security or declaring explicit requirements
requires a maintainer decision because the scheme binding is unresolved. Explicitly
empty and optional-anonymous declarations also require semantic revalidation. A
future implementation phase must explicitly reconfirm the selected operation's
authentication strategy; it cannot select authentication from `auth_status` alone.

Likewise, `file_upload_surface_present` is proposal-level evidence. It creates an
attribution gap but does not make every approved operation unsupported. Only local,
unambiguous multipart evidence makes that operation unsupported; other media such as
`application/octet-stream` require an extension without inventing file semantics.

Base paths and operation paths are joined without decoding or traversal
normalization. Query, fragment, backslash, traversal segments, and ambiguous double
slashes fail closed. Static effective paths become exact-path candidates. Dynamic
paths record the need for a maintainer-owned `SafePathTemplate`; no template is
created.

## Provider-definition field matrix

Origin, allowed-host candidate, allowed-method candidates, static exact-path
candidates, initial disabled state, and redirect denial are design metadata only.
Operational policy and identity fields—including API ID, description, risk, cost,
latency, timeout, response/body limits, cache, retry count, rate limiting,
provenance, credentials, auth header, and feature gate—remain unresolved. The plan
always retains proposal risk signals and review blockers.

Callbacks and webhooks are excluded from implementation scope. External reference
resolution remains deferred and never causes a fetch. Mutating methods retain their
mutation signal and require an explicit mutation-policy design.

## Offline CLI

`scripts/external_api_implementation_plan.py` accepts only proposal, approval,
scaffold, and output-directory paths. It writes exactly:

- `provider-implementation-plan.json`
- `README.md`
- `runtime-compatibility.md`

All outputs are inert JSON or Markdown. The analysis performs no DNS or HTTP access.

## Authority chain

```text
Discovery
  -> OpenAPI Intake
  -> ProviderDesignProposal v2 (all execution authority false)
  -> HumanApprovalManifest v1 (scaffold generation only)
  -> NonExecutableProviderScaffold v2 (all execution authority false)
  -> StaticProviderImplementationPlan v2 (all code/execution authority false)
```

## Attribution threats

The v2 analysis fails closed against global security-scheme over-attribution, unused
security-scheme poisoning, operation security-binding ambiguity, global file-upload
signal over-attribution, and false incompatibility propagation. Uncertainty becomes
an explicit plan gap or maintainer decision, never an inferred operation binding.

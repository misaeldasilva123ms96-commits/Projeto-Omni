# External API human approval and inert scaffolds

Phase 9 introduces an offline, explicitly human boundary:

```text
Discovery
→ Schema Intake
→ ProviderDesignProposal v2
→ Human Review
→ Approval Manifest v1
→ Non-Executable Scaffold v2
```

Human approval authorizes only creation of a design scaffold. It does not authorize executable
code generation, provider or tool registration, credentials, network access, runtime activation,
or execution of an API operation.

## Proposal and snapshot binding

An approval preserves five immutable bindings: `proposal_id`, `proposal_format_version`,
`candidate_id`, `canonical_schema_sha256`, and `proposal_snapshot_sha256`. The snapshot hash is
SHA-256 over canonical JSON of the complete normalized proposal. It detects changes outside the
proposal ID, including operation metadata, issues, and review blockers.

SHA-256 supplies tamper detection and identity binding; it is not a digital signature and does not
authenticate a reviewer. `reviewed_by` is a normalized, human-entered self-attestation label.
`reviewer_identity_cryptographically_verified` is always false in Phase 9.

## Explicit review scope

Every checklist decision starts false. Terms, security, privacy, cost, rate limits, provider
documentation, and implementation scope must all be explicitly accepted. Review blockers must be
acknowledged as an exact set. The reviewer selects one to twenty complete proposal operations,
acknowledges every selected mutation and security exception, and confirms the exact hostname of
the sole eligible declared HTTPS server.

Scaffold v2 excludes unsupported/custom methods, invalid security declarations, templated or
insecure servers, non-standard ports, IP literals, local/single-label names, ambiguous servers,
callbacks, and webhooks from executable scope. No DNS lookup or HTTP request is performed.

## Integrity and future promotion

The three identity levels have separate purposes:

- `proposal_snapshot_sha256` binds an approval to the exact proposal reviewed by the human;
- `approval_id` binds the human review decision, scope, acknowledgements, and proposal bindings;
- `scaffold_id` binds the exact canonical content of the derived scaffold, excluding only its own
  ID.

The approval and scaffold IDs hash canonical JSON of their complete serialized content, excluding
only their respective ID fields. Verification recomputes each hash and enforces authority
invariants. A content-bound scaffold ID detects accidental or unrehashed tampering; it does not
authenticate who created the scaffold. An attacker who changes and rehashes content creates a
different artifact.

`verify_scaffold_against_approval_and_proposal` therefore also verifies the approval against the
proposal, deterministically rederives the expected scaffold, and compares the entire supplied
artifact. This detects a rehashed scaffold that was not derived from the original approval and
proposal. Writers emit only `provider-scaffold.json` and `README.md`, using fixed names and atomic
replacement.

A later implementation phase must rerun discovery and schema intake, recreate the proposal, and
verify all five approval bindings before using approved design data. Any changed candidate, schema,
proposal semantic format, or proposal snapshot produces `approval_stale`; there is no automatic
promotion.

## Authority matrix

| Artifact | Scaffold | Executable code | Registration | Network | Execution |
| --- | ---: | ---: | ---: | ---: | ---: |
| DiscoveryCandidate | false | false | false | false | false |
| ProviderDesignProposal | false | false | false | false | false |
| HumanApprovalManifest | true | false | false | false | false |
| NonExecutableProviderScaffold | false | false | false | false | false |
| StaticProviderImplementationPlan | false | false | false | false | false |

The next offline boundary is the
[`StaticProviderImplementationPlan v1`](external-api-static-implementation-plan.md).
It fully revalidates proposal v2, approval v1, and scaffold v2 before comparing the
approved design surface with a fingerprinted description of current runtime
capabilities. The resulting plan grants no source-code, provider-definition,
credential, feature-gate, registration, network, tool, or runtime-activation
authority.

## Threat model

The boundary fails closed for tampered proposal files, stale proposals, changed schemas or proposal
formats, missing or invented blocker acknowledgements, arbitrary host injection, server ambiguity,
operation injection, mutation-scope escalation, anonymous-security oversight, tampered scaffolds,
rehashed tampered scaffolds, nested JSON field smuggling, discarded nested `source` fields, path
encoding ambiguity, manifest/scaffold authority tampering, prompt-injection text, and automatic
authority promotion. Validation is deterministic and uses no LLM, unsafe deserializer, subprocess,
network client, or runtime registry.

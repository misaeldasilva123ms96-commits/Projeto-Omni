# External API human approval and inert scaffolds

Phase 9 introduces an offline, explicitly human boundary:

```text
Discovery
→ Schema Intake
→ ProviderDesignProposal v2
→ Human Review
→ Approval Manifest v1
→ Non-Executable Scaffold v1
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

Scaffold v1 excludes unsupported/custom methods, invalid security declarations, templated or
insecure servers, non-standard ports, IP literals, local/single-label names, ambiguous servers,
callbacks, and webhooks from executable scope. No DNS lookup or HTTP request is performed.

## Integrity and future promotion

The approval ID hashes canonical JSON of all approval content except the ID itself. Verification
recomputes it, enforces authority invariants, and compares the five proposal bindings. Scaffold ID
is deterministic over approval ID and scaffold format version. Writers emit only
`provider-scaffold.json` and `README.md`, using fixed names and atomic replacement.

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

## Threat model

The boundary fails closed for tampered proposal files, stale proposals, changed schemas or proposal
formats, missing or invented blocker acknowledgements, arbitrary host injection, server ambiguity,
operation injection, mutation-scope escalation, anonymous-security oversight, manifest/scaffold
authority tampering, prompt-injection text, and automatic authority promotion. Validation is
deterministic and uses no LLM, unsafe deserializer, subprocess, network client, or runtime registry.

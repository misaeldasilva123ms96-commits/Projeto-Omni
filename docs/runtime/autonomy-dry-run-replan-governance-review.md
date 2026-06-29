# Autonomy Dry-Run Replan Governance Review

**Date:** 2026-06-29
**Branch:** `feature/autonomy-dry-run-replan-governance-review`
**Base:** `main` after PR #445
**Status:** Governance review only
**Runtime impact:** None

## 1. Executive Summary

The dry-run REPLAN stack is suitable for documentation and read-only
diagnostics. It provides a safe planning artifact, safe interpretation notes,
and Cockpit visibility for reviewers without rewriting prompts, executing
replans, executing retries, calling providers/models again, changing provider
routing, or changing runtime output.

This review does not approve execution. The current stack remains
advisory-only and dry-run planning only.

Governance conclusion:

- Approved for documentation and readonly diagnostics.
- Approved for safe evidence persistence design only after this review.
- Not approved for prompt rewriting.
- Not approved for provider/model retry or replan execution.
- Not approved for autonomous execution.

## 2. Scope

This review covers the dry-run REPLAN planning stack after the design,
contracts, runtime inspection metadata, Cockpit readonly display, and evidence
interpretation notes.

It reviews:

- Runtime behavior boundaries.
- Cockpit behavior boundaries.
- Evidence and auditability.
- Safety, redaction, and privacy constraints.
- Operator interpretation risks.
- Required controls before any persistence, execution design, or autonomous
  execution.

It does not implement code, change runtime behavior, change provider routing,
rewrite prompts, execute actions, add persistence, or approve autonomous
execution.

## 3. Current REPLAN Stack Inventory

The current dry-run REPLAN stack includes:

- `docs/runtime/autonomy-dry-run-replan-plan-design.md`.
- `DryRunReplanPlan` model.
- `DryRunReplanPlanner`.
- Safe serialization through `as_dict`.
- Eligibility and blocking rules.
- Safe categorical `suggested_strategy`.
- Bounded and sanitized `evidence_summary`.
- Runtime inspection metadata at
  `autonomy_evaluation.dry_run_replan_plan`.
- Cockpit Autonomia tab readonly display.
- Evidence interpretation notes at
  `docs/runtime/autonomy-dry-run-replan-plan-evidence-notes.md`.

The stack is a planning and observability surface only. It is not connected to
prompt rewriting, provider calls, model calls, tool calls, command execution,
file writes, CI repair, provider switching, self-repair, Git automation, or PR
automation.

## 4. Runtime Behavior Review

Runtime behavior remains unchanged except for attaching safe inspection
metadata. The plan is generated as advisory metadata and displayed for review.
It must not be consumed by runtime execution paths.

Required runtime guarantees:

- No prompt rewrite.
- No rewritten prompt generation.
- No second provider/model call.
- No retry execution.
- No replan execution.
- No response string mutation.
- No provider routing mutation.
- No tool execution.
- No command execution.
- No file write or code patch.
- No CI repair.
- No commit, push, or PR automation.

The runtime may expose `dry_run_replan_plan` as diagnostics only. It must not
treat `would_replan=true`, `blocked=false`, `replan_eligibility_score`, or
`suggested_strategy` as authorization.

## 5. Cockpit Behavior Review

The Cockpit Autonomia tab displays dry-run REPLAN plan metadata as readonly
diagnostics with the operator-facing label that no replan was executed.

Cockpit visibility is not operational authorization. The tab must not expose:

- Replan buttons.
- Retry buttons.
- Prompt rewrite controls.
- Provider-switch controls.
- Tool execution controls.
- Command execution controls.
- Patch controls.
- CI repair controls.
- Commit/push/PR controls.
- Destructive cleanup or persistence controls tied to the plan.

Missing plan metadata should remain an empty or unavailable state. It must not
be interpreted as approval, denial, or permission to execute.

## 6. Evidence and Auditability Review

The plan evidence is useful for review because it records safe metadata:

- Plan identity.
- Plan type.
- Advisory flag.
- Eligibility boolean.
- Blocked boolean.
- Safe block categories.
- Safe eligibility score.
- Safe risk level.
- Source decision.
- Fingerprint ID.
- Progress and stagnation scores.
- Repeated strategy count.
- Safe categorical strategy suggestion.
- Creation timestamp.

Evidence must remain bounded, sanitized, and metadata-only. Reviewers may cite
safe fields in governance notes, but must not expand them with raw runtime
material.

If evidence persistence is designed later, it must store only sanitized
metadata and must preserve the same forbidden-field boundaries.

## 7. Safety Boundary Review

The safety boundary is currently adequate for documentation and read-only
diagnostics because the planner is pure and advisory.

Required safety boundaries:

- `would_replan=true` is not permission.
- `blocked=false` is not permission.
- `suggested_strategy` is not an instruction.
- `replan_eligibility_score` is not an approval signal.
- Cockpit visibility is not operational authorization.
- No dry-run plan may trigger an executor.
- No dry-run plan may mutate runtime response.
- No dry-run plan may mutate provider routing.
- No dry-run plan may write prompts, files, patches, commits, pushes, PRs, or
  CI state.

These boundaries must remain explicit in future design and implementation
work.

## 8. Redaction/Privacy Review

Dry-run REPLAN evidence must never include:

- Raw prompt.
- Rewritten prompt.
- Raw response.
- Raw provider payload.
- Raw receipt.
- Stack trace or traceback.
- stdout/stderr.
- Command args.
- Headers or cookies.
- API keys, tokens, secrets, or provider credentials.
- File contents.
- `.env` content.
- Full tool output.
- Raw database rows.
- Raw session state dumps.

Allowed evidence must stay categorical, boolean, numeric, timestamped, or
bounded sanitized strings. Any future persistence, UI display, audit export, or
review summary must enforce the same allowlist.

## 9. Governance Decision Review

The governance decision for the current stack is:

- Approved for documentation and readonly diagnostics.
- Approved for safe evidence persistence design only after this review.
- Not approved for prompt rewriting.
- Not approved for provider/model retry or replan execution.
- Not approved for autonomous execution.

The current REPLAN plan may inform human review and future safe design work.
It may not authorize runtime behavior changes.

Any future proposal that adds persistence, prompt rewriting, provider/model
calls, retry execution, replan execution, provider switching, self-repair, CI
repair, or Git/PR automation requires a separate design and go/no-go review.

## 10. Operator Interpretation Risks

Primary interpretation risks:

- Operators may treat `would_replan=true` as permission.
- Operators may treat `blocked=false` as permission.
- Operators may treat `suggested_strategy` as an instruction.
- Operators may treat `replan_eligibility_score` as an approval signal.
- Operators may treat Cockpit visibility as operational authorization.
- Operators may paste raw prompts, rewritten prompts, responses, tool output,
  logs, provider payloads, or secrets into review notes.
- Operators may assume a stale `fingerprint_id` proves the current failure
  context.

The evidence notes mitigate these risks, but future UI and persistence work
must continue to reinforce them.

## 11. Abuse/Misuse Cases

Misuse cases to guard against:

- A developer wires `would_replan=true` into a prompt rewrite path.
- A developer treats `suggested_strategy` as executable planning instructions.
- A UI adds a Replan button beside the readonly panel.
- A future persistence layer stores raw prompts or rewritten prompts for audit
  convenience.
- A reviewer copies raw provider payloads or full tool outputs into an issue.
- A future automation uses `blocked=false` to bypass human approval.
- A future provider router uses dry-run REPLAN metadata to switch providers.
- CI repair or Git automation interprets the plan as a work item.

These cases remain explicitly out of scope and must be blocked by review,
tests, and governance gates.

## 12. Failure Modes

Important failure modes:

- Planner fails and diagnostics are missing.
- Plan metadata is malformed or partially missing.
- Plan metadata is stale relative to the latest runtime turn.
- Fingerprint correlation is ambiguous.
- Scores are misunderstood without surrounding context.
- Cockpit displays an empty plan and an operator interprets it as approval.
- Redaction misses a secret-like string in future evidence fields.
- Future persistence stores unsafe fields.
- Future tests assert shape but not safety boundaries.

Required response: degrade to safe empty diagnostics, keep runtime output
unchanged, avoid execution, and require manual review for ambiguous evidence.

## 13. Required Controls Before Persistence

Before any dry-run REPLAN evidence persistence design is approved, require:

- Explicit metadata-only schema.
- Field allowlist matching the safe plan contract.
- Forbidden-field tests for raw prompt, rewritten prompt, response, payloads,
  credentials, secrets, traces, command args, file contents, `.env`, tool
  outputs, raw receipts, and raw rows.
- Bounded string lengths and bounded list lengths.
- Safe categorical `suggested_strategy` only.
- Best-effort writes and safe read degradation.
- Corruption handling that returns empty/safe metadata.
- TTL and cleanup design if persisted beyond transient inspection.
- SQLite opt-in or explicitly approved storage mode.
- Documentation that persistence is not execution approval.
- Governance review before implementation.

## 14. Required Controls Before Any Execution Design

Before any execution design is even considered, require:

- Separate design document for supervised dry-run-to-execution transition.
- Explicit human approval model.
- Prompt rewrite threat model.
- Provider/model call threat model.
- Runtime output preservation analysis.
- Provider routing preservation or explicit routing governance review.
- Safety gates for high/critical risk, secrets, protected files, destructive
  actions, tool/command/write requirements, unsafe CI/security signals, no safe
  next action, and user approval requirements.
- Audit plan that remains metadata-only by default.
- Tests proving no execution occurs unless a future approved execution mode is
  explicitly enabled.
- Separate go/no-go review.

This review does not approve execution design work that implements behavior.

## 15. Required Controls Before Autonomous Execution

Before autonomous execution can be considered, require:

- Executive governance approval.
- Human approval and override controls.
- Explicit autonomy operating model update.
- Strong secrets and protected-file enforcement.
- Provider routing governance.
- Prompt rewrite safety review.
- Tool/command/file-write sandboxing.
- CI repair governance.
- Commit/push/PR automation governance.
- Rollback and incident response procedures.
- Observability and audit trails.
- Red-team or abuse-case review.
- Full CI and security validation gates.
- Separate production readiness review.

Omni remains advisory-only until all required controls are designed,
implemented, validated, reviewed, and explicitly approved.

## 16. Explicit Non-Approval Statement

This review does not approve:

- Prompt rewriting.
- Rewritten prompt generation.
- Provider/model retry execution.
- Provider/model replan execution.
- Automatic retry.
- Automatic replan.
- Provider switching.
- Self-repair.
- Tool execution.
- Command execution.
- File writes.
- Patching.
- CI repair.
- Commit, push, or PR automation.
- Autonomous execution.

The dry-run REPLAN stack is evidence and diagnostics only.

## 17. Open Risks

Open risks:

- Operators may still over-trust safe-looking scores and booleans.
- Future persistence may accidentally expand the field set.
- Future UI changes may turn readonly diagnostics into controls.
- Evidence summaries may be manually expanded with unsafe raw material.
- Fingerprint correlation may become stale or ambiguous.
- Governance language may be copied without the non-approval warning.
- Broad safety scans can be noisy because tests and docs include forbidden
  examples; reviewers must distinguish examples from actual leaks.

## 18. Open Questions

Open questions before future phases:

- Should safe evidence persistence store REPLAN plans in the same store as
  autonomy decision evidence or a separate table/log?
- What TTL should apply to persisted dry-run REPLAN evidence?
- Should Cockpit show stale-plan indicators?
- Should Cockpit include a safe copy-to-review checklist?
- How should dry-run RETRY and dry-run REPLAN evidence be compared in one
  operator view?
- Which governance role can approve a transition from read-only diagnostics to
  supervised execution design?
- What minimum CI/security gate must pass before any persistence PR?

## 19. Go/No-Go Table

| Area | Decision | Required next action |
|------|----------|----------------------|
| Documentation | Go | Continue maintaining design, evidence notes, and governance docs. |
| Readonly runtime diagnostics | Go | Keep metadata-only and best-effort. |
| Cockpit readonly display | Go | Keep no-action labels and no controls. |
| Safe evidence persistence design | Conditional Go | May start only after this review, with metadata-only schema and redaction controls. |
| Evidence persistence implementation | No-Go | Requires approved design, tests, and separate PR. |
| Prompt rewriting | No-Go | Requires separate execution design and governance approval. |
| Provider/model retry execution | No-Go | Requires separate execution design and governance approval. |
| Provider/model replan execution | No-Go | Requires separate execution design and governance approval. |
| Provider switching | No-Go | Requires separate provider-routing governance review. |
| Tool/command/file execution | No-Go | Requires sandbox, approval model, and execution governance. |
| CI repair | No-Go | Requires separate CI repair governance review. |
| Commit/push/PR automation | No-Go | Requires separate repository automation governance review. |
| Autonomous execution | No-Go | Requires full autonomy operating model approval and production readiness review. |

## 20. Final Recommendation

Final recommendation:

- Approved for documentation and readonly diagnostics.
- Approved for safe evidence persistence design only after this review.
- Not approved for prompt rewriting.
- Not approved for provider/model retry or replan execution.
- Not approved for autonomous execution.

Required warnings remain in force:

- `would_replan=true` is not permission.
- `blocked=false` is not permission.
- `suggested_strategy` is not an instruction.
- `replan_eligibility_score` is not an approval signal.
- Cockpit visibility is not operational authorization.
- Persistence, if added later, must store only sanitized metadata.
- Omni remains advisory-only.

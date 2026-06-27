# Autonomy Dry-Run Retry Plan Design

**Date:** 2026-06-27
**Branch:** `feature/autonomy-dry-run-retry-plan-design`
**Base:** `main` after PR #437
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a safe dry-run RETRY planning layer for Omni's advisory
autonomy stack.

Dry-run RETRY planning may describe whether Omni would consider retrying a
failed runtime interaction, why it would or would not retry, and which safety
constraints apply. It must not perform the retry. It must not make a second
provider call, repeat a model call, change provider routing, change runtime
output, execute tools, write files, patch code, repair CI, or automate Git.

The design is approved only as a future planning contract. It is not approval
for autonomous execution.

**Contracts update:** `feature/autonomy-dry-run-retry-plan-contracts` adds the
safe `DryRunRetryPlan` model, a pure `DryRunRetryPlanner`, and tests for the
metadata-only contract. The planner is not wired into retry execution, does not
call providers, does not repeat model calls, and does not change runtime
responses or provider routing.

## 2. Current Status

The current autonomy stack is advisory-only. It includes:

- Advisory Autonomy Controller.
- Per-session autonomy state.
- Smart Error Progress Tracker.
- Tracker-aware policy.
- Persisted advisory evidence.
- Read-only Cockpit visibility.
- SQLite opt-in session state persistence.
- Cleanup lifecycle and dry-run cleanup tooling.
- A pre-dry-run review that approved only dry-run planning work.

No RETRY, REPLAN, SELF_REPAIR, SWITCH_PROVIDER, ABORT_SAFE, CI repair,
provider switching, patching, or repository automation is approved for
execution.

## 3. Problem Statement

The advisory autonomy stack can recommend RETRY, but there is no bounded
planning artifact that explains what a retry would mean without performing it.
Before any supervised or real retry execution is considered, Omni needs a
metadata-only dry-run plan that can answer:

- Would retry be eligible?
- Why would retry be eligible or blocked?
- What evidence supports the decision?
- What safety gates would prevent execution?
- What limits would apply if retry were ever implemented later?

The plan must improve reviewability without introducing an execution path.

## 4. Goals

- Define dry-run RETRY as plan-only advisory metadata.
- Keep `advisory=true` and `plan_type=dry_run_retry`.
- Preserve runtime output exactly.
- Preserve provider routing exactly.
- Reuse safe autonomy evidence, tracker scores, and session state metadata.
- Define explicit eligibility and blocking rules.
- Define a safe plan result schema.
- Define evidence/audit behavior without raw payload persistence.
- Define Cockpit visibility as read-only and non-executable.
- Define tests required for any future implementation.

## 5. Non-Goals

- Do not implement retry execution.
- Do not implement replan execution.
- Do not add an executor for advisory decisions.
- Do not add a scheduler or automatic loop.
- Do not make a second provider call.
- Do not repeat a model call.
- Do not change runtime output.
- Do not change provider routing.
- Do not execute tools or commands.
- Do not write files, patch code, repair CI, commit, push, or open PRs.
- Do not persist raw prompts, responses, receipts, provider payloads, tool
  output, stack traces, secrets, credentials, or file contents.

## 6. Dry-Run RETRY Definition

Dry-run RETRY means:

- Build a safe plan describing whether a retry would be considered.
- Explain eligibility, block reasons, risk, and evidence summary.
- Return metadata only.
- Mark the result as `advisory=true`.
- Mark the result as `plan_type=dry_run_retry`.
- Preserve the original runtime response string.
- Avoid all provider calls and all tool execution.

Dry-run RETRY is not a retry. It is a review artifact for a future phase.

## 7. What Dry-Run RETRY Must Never Do

Dry-run RETRY must never:

- Make a second provider call.
- Repeat a model call.
- Change the response string.
- Switch providers.
- Execute a tool.
- Execute a command.
- Patch code.
- Write files.
- Commit, push, or open a PR.
- Repair CI.
- Modify secrets, `.env`, deploy config, CI secrets, or production settings.
- Persist raw prompt, raw response, raw receipt, raw provider payload, raw tool
  output, stack trace, traceback, stdout/stderr, command args, headers,
  cookies, API keys, tokens, provider credentials, file contents, or `.env`
  content.

## 8. Inputs

Allowed inputs are safe metadata already available to the advisory autonomy
stack:

- Advisory decision and recommended decision hint.
- Risk level.
- Safe reason category.
- Fingerprint ID.
- Progress score.
- Stagnation score.
- Repeated strategy count.
- Current error count.
- Stagnant attempts.
- Safe last error type.
- Safe runtime mode.
- Safe provider failure type.
- Safe response length only, not response content.
- Safe fallback flag.
- Safe session state source and degradation metadata.
- Governance status such as pause, escalation, or abort-safe category.
- Configured retry attempt limit.

Forbidden inputs include raw prompts, raw responses, raw provider payloads,
raw receipts, stack traces, stdout/stderr, command args, secrets, credentials,
headers, cookies, file contents, and `.env` content.

## 9. Outputs

The output is a dry-run retry plan. It is safe, bounded metadata only.

The output must not include:

- Raw prompt.
- Raw response.
- Raw provider payload.
- Raw receipt.
- Stack trace or traceback.
- stdout/stderr.
- Command args.
- Headers or cookies.
- API keys, tokens, secrets, or provider credentials.
- File contents or `.env` content.

The output must clearly state whether retry would be eligible and whether it is
blocked.

## 10. Decision/Evidence Sources

Dry-run RETRY planning may use:

- `AutonomyController` advisory decision metadata.
- Tracker-aware policy output.
- `SmartErrorProgressTracker` scores and fingerprint ID.
- `AutonomySessionTracker` safe session counters.
- MemoryFacade advisory evidence, if available.
- SQLite opt-in session state metadata, if available.
- Cockpit-safe autonomy diagnostics.
- Governance pause/escalate/abort-safe metadata.

Reads must degrade safely. Missing evidence should produce a blocked or
low-confidence plan, not execution.

## 11. Retry Eligibility Rules

Retry may be eligible only when all of the following are true:

- The advisory decision is RETRY, or the recommended decision hint is
  retry-like.
- Risk is low or medium.
- No secret is detected.
- No protected file is involved.
- No destructive operation is involved.
- Provider routing would remain unchanged.
- Retry count remains under the configured limit.
- Runtime output would not be changed.
- No tool execution is required.
- No command execution is required.
- No file write is required.
- No governance pause, escalation, or abort-safe signal blocks the plan.

Eligibility does not authorize execution. It only means the plan may report
`would_retry=true`.

## 12. Retry Blocking Rules

Retry must be blocked when any of the following are true:

- Risk is high or critical.
- A secret is detected.
- A protected file is touched.
- Provider switching is required.
- Tool, write, command, or destructive action is required.
- CI or security signal is unsafe.
- There is no safe next action.
- Max retry attempts are exceeded.
- Governance decision says pause, escalate, or abort.
- User approval is required.
- Required evidence is missing or corrupt in a way that prevents safe planning.
- Any required field would need raw prompt, response, provider payload, command
  args, file contents, or secrets.

Blocked plans must return `would_retry=false`, `blocked=true`, and safe
`block_reasons`.

## 13. Safety Gates

Every dry-run RETRY plan must pass these gates:

- `advisory=true`.
- `plan_type=dry_run_retry`.
- No provider call can be made.
- No model call can be repeated.
- No runtime response can be changed.
- No provider routing can change.
- No tool or command can execute.
- No file can be written.
- No patching can occur.
- No CI repair can occur.
- No commit, push, or PR can occur.
- Output fields must be allowlisted.
- Strings must be bounded and sanitized.
- Missing storage or corrupt evidence must degrade safely.

## 14. Plan Result Schema

Proposed fields:

| Field | Type | Notes |
|-------|------|-------|
| `plan_id` | string | Stable unique plan identifier, no raw payload material |
| `plan_type` | string | Must be `dry_run_retry` |
| `advisory` | boolean | Must be `true` |
| `would_retry` | boolean | True only if eligible and not blocked |
| `retry_reason` | string | Safe bounded reason category or summary |
| `blocked` | boolean | True when retry must not be planned |
| `block_reasons` | string array | Safe bounded categories |
| `retry_eligibility_score` | number | Bounded score, implementation-defined |
| `risk_level` | string | Safe enum-like risk value |
| `source_decision` | string | Advisory decision name, such as `RETRY` |
| `fingerprint_id` | string | Safe fingerprint ID |
| `stagnation_score` | number | Existing safe tracker score |
| `progress_score` | number | Existing safe tracker score |
| `repeated_strategy_count` | integer | Non-negative count |
| `max_attempts_remaining` | integer | Non-negative remaining retry budget |
| `evidence_summary` | string | Sanitized bounded summary |
| `created_at` | timestamp | UTC ISO-8601 |

Example:

```json
{
  "plan_id": "dry-retry-20260627-abc123",
  "plan_type": "dry_run_retry",
  "advisory": true,
  "would_retry": true,
  "retry_reason": "transient_provider_timeout",
  "blocked": false,
  "block_reasons": [],
  "retry_eligibility_score": 0.74,
  "risk_level": "medium",
  "source_decision": "RETRY",
  "fingerprint_id": "fp_123",
  "stagnation_score": 2,
  "progress_score": 1,
  "repeated_strategy_count": 0,
  "max_attempts_remaining": 1,
  "evidence_summary": "retry eligible from safe timeout metadata",
  "created_at": "2026-06-27T00:00:00+00:00"
}
```

## 15. Evidence/Audit Behavior

Dry-run RETRY plans may be recorded as safe evidence only if a future
implementation has an explicit metadata-only persistence contract.

Evidence may include:

- Plan ID.
- Plan type.
- Advisory flag.
- Eligibility and block status.
- Safe block reason categories.
- Risk level.
- Source decision.
- Fingerprint ID.
- Progress/stagnation scores.
- Attempt budget remaining.
- Safe evidence summary.
- Created timestamp.

Evidence must not include raw prompts, responses, provider payloads, receipts,
stack traces, stdout/stderr, command args, headers, cookies, secrets,
credentials, file contents, `.env` content, or raw database rows.

## 16. Cockpit Visibility Proposal

Cockpit may show dry-run RETRY plans only as read-only diagnostics.

Allowed Cockpit fields:

- Plan ID.
- Plan type.
- Advisory flag.
- Would retry.
- Blocked.
- Block reasons.
- Retry reason.
- Eligibility score.
- Risk level.
- Source decision.
- Fingerprint ID.
- Progress/stagnation scores.
- Max attempts remaining.
- Created timestamp.

Cockpit must not expose a Retry button, destructive control, provider switch
control, patch control, CI repair control, or commit/push/PR control. Cockpit
must not render raw prompts, responses, provider payloads, stack traces,
stdout/stderr, command args, secrets, or file contents.

## 17. Runtime Behavior Guarantees

Dry-run RETRY planning must guarantee:

- Runtime response string unchanged.
- Provider routing unchanged.
- No provider call.
- No repeated model call.
- No tool execution.
- No command execution.
- No file write.
- No patching.
- No CI repair.
- No Git or PR automation.
- No background scheduling.
- No automatic loop.
- Failures degrade to missing, blocked, or degraded plan metadata.

The planner must never sit on the critical path in a way that can block or
alter the user's runtime response.

## 18. Testing Plan

Future implementation must add tests for:

- RETRY advisory decision produces a dry-run plan only.
- Retry-like hint produces a dry-run plan only.
- No second provider call is made.
- No model call is repeated.
- Runtime response string is unchanged.
- Provider routing is unchanged.
- High/critical risk blocks retry.
- Secret detection blocks retry.
- Protected-file signal blocks retry.
- Tool/write/destructive requirement blocks retry.
- Unsafe CI/security signal blocks retry.
- Max attempts exceeded blocks retry.
- Governance pause/escalate/abort blocks retry.
- Missing/corrupt evidence degrades safely.
- Output contains only allowlisted fields.
- Forbidden fields are not persisted or rendered.
- Cockpit display, if implemented, is read-only.

## 19. Rollout Plan

Recommended rollout:

1. Design review and approval.
2. Add model/contracts only, with no runtime wiring.
3. Add tests proving no execution paths exist.
4. Add optional read-only MemoryFacade evidence contract, if approved.
5. Add opt-in runtime inspection attachment, if it cannot change runtime
   output.
6. Add read-only Cockpit display, if needed.
7. Run focused autonomy, memory, security, and UI tests as applicable.
8. Require a separate go/no-go review before any real retry execution design.

## 20. Known Risks

- Operators may confuse `would_retry=true` with approval to retry.
- Future wiring may accidentally perform a second provider call.
- Eligibility scores can be over-trusted.
- Missing evidence may produce false negatives.
- Stale session state may affect planning quality.
- Future Cockpit work could accidentally add action controls.
- Evidence summaries could drift toward raw payload detail if allowlists are
  not enforced.

## 21. Open Questions

- What retry attempt limit should dry-run planning assume by default?
- Should eligibility score be rule-based only or weighted by tracker scores?
- Should dry-run RETRY plans be persisted by default or attached only to
  runtime inspection?
- Should Cockpit show blocked plans, eligible plans, or both?
- Should `recommended_decision_hint` values be normalized into a small enum?
- Should dry-run RETRY and dry-run REPLAN share a common plan base model?

## 22. Go/No-Go Checklist

| Gate | Result |
|------|--------|
| Design is documentation-only | Go |
| Dry-run RETRY is plan-only | Go |
| No provider call allowed | Go |
| No repeated model call allowed | Go |
| Runtime output must remain unchanged | Go |
| Provider routing must remain unchanged | Go |
| Tool/command/file execution forbidden | Go |
| Patching/CI repair/Git automation forbidden | Go |
| Output schema is metadata-only | Go |
| Raw prompt/response/provider payload forbidden | Go |
| Cockpit proposal is read-only | Go |
| Real RETRY execution approved | No-go |
| REPLAN execution approved | No-go |
| SELF_REPAIR approved | No-go |
| Provider switching approved | No-go |
| CI repair approved | No-go |
| Commit/push/PR automation approved | No-go |

## 23. Final Recommendation

Proceed with a future implementation branch for dry-run RETRY planning
contracts only.

Do not implement retry execution. Do not make provider calls. Do not repeat
model calls. Do not change runtime output. Do not change provider routing. Do
not add scheduler, automatic loops, tool execution, file writes, patching, CI
repair, provider switching, or repository automation.

The next implementation phase should produce metadata-only dry-run plans and
tests proving that no autonomous action can occur.

# Autonomy Dry-Run Replan Plan Design

**Date:** 2026-06-27
**Branch:** `feature/autonomy-dry-run-replan-plan-design`
**Base:** `main` after PR #441
**Status:** Design only
**Runtime impact:** None

## 1. Executive Summary

This document designs a safe dry-run REPLAN planning layer for Omni's
advisory autonomy stack.

Dry-run REPLAN planning may describe whether Omni would consider changing its
future strategy, why a replan would or would not be eligible, and which safety
constraints apply. It must not rewrite prompts, perform a replan, make a
second provider/model call, change provider routing, change runtime output,
execute tools, write files, patch code, repair CI, or automate Git/PR work.

The design is approved only as a future planning contract. It is not approval
for autonomous execution.

**Contracts update:** `feature/autonomy-dry-run-replan-plan-contracts` adds the
safe `DryRunReplanPlan` model, a pure `DryRunReplanPlanner`, safe
serialization, bounded evidence summaries, safe categorical
`suggested_strategy`, and tests for the metadata-only contract. The planner is
not wired into replan execution, does not rewrite prompts, does not call
providers, does not repeat model calls, and does not change runtime responses
or provider routing.

## 2. Current Status

The current autonomy mode is advisory-only and dry-run planning only.

The dry-run RETRY stack already includes:

- `DryRunRetryPlan` contracts.
- `DryRunRetryPlanner`.
- Runtime Inspector and Cockpit observability.
- Evidence interpretation notes.

No RETRY, REPLAN, SELF_REPAIR, SWITCH_PROVIDER, ABORT_SAFE, CI repair,
provider switching, prompt rewriting, patching, or repository automation is
approved for execution.

## 3. Problem Statement

The advisory autonomy stack can recommend REPLAN, but there is not yet a
bounded planning artifact that explains what a replan would mean without
rewriting prompts or performing actions.

Before any supervised or real replan execution is considered, Omni needs a
metadata-only dry-run plan that can answer:

- Would replan be eligible?
- Why would replan be eligible or blocked?
- What evidence suggests the current approach is stuck?
- What safe strategy category might be considered later?
- Which safety gates would prevent execution?

The plan must improve reviewability without introducing a prompt rewrite or
execution path.

## 4. Goals

- Define dry-run REPLAN as plan-only advisory metadata.
- Keep `advisory=true` and `plan_type=dry_run_replan`.
- Preserve runtime output exactly.
- Preserve provider routing exactly.
- Preserve the original prompt exactly.
- Reuse safe autonomy evidence, tracker scores, session state metadata, and
  dry-run RETRY lessons.
- Define explicit eligibility and blocking rules.
- Define a safe plan result schema.
- Define evidence/audit behavior without raw payload persistence.
- Define Cockpit visibility as read-only and non-executable.
- Define tests required for any future implementation.

## 5. Non-Goals

- Do not implement replan execution.
- Do not implement retry execution.
- Do not rewrite prompts.
- Do not call a provider/model again.
- Do not repeat a model call.
- Do not change runtime output.
- Do not change provider routing.
- Do not execute tools or commands.
- Do not write files, patch code, repair CI, commit, push, or open PRs.
- Do not add a scheduler or automatic loop.
- Do not enable provider switching.
- Do not enable self-repair.
- Do not persist raw prompts, rewritten prompts, responses, receipts, provider
  payloads, tool output, stack traces, secrets, credentials, or file contents.

## 6. Dry-Run REPLAN Definition

Dry-run REPLAN means:

- Build a safe plan describing whether a replan would be considered.
- Explain eligibility, block reasons, risk, suggested safe strategy category,
  and evidence summary.
- Return metadata only.
- Mark the result as `advisory=true`.
- Mark the result as `plan_type=dry_run_replan`.
- Preserve the original prompt and runtime response string.
- Avoid all provider/model calls and all tool execution.

Dry-run REPLAN is not a replan. It is a review artifact for a future phase.

## 7. What Dry-Run REPLAN Must Never Do

Dry-run REPLAN must never:

- Rewrite a prompt.
- Generate a rewritten prompt.
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
- Persist raw prompt, rewritten prompt, raw response, raw receipt, raw provider
  payload, raw tool output, stack trace, traceback, stdout/stderr, command
  args, headers, cookies, API keys, tokens, provider credentials, file
  contents, or `.env` content.

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
- Safe strategy names already attempted.
- Current error count.
- Stagnant attempts.
- Safe last error type.
- Safe runtime mode.
- Safe provider failure type.
- Safe response length only, not response content.
- Safe fallback flag.
- Safe session state source and degradation metadata.
- Governance status such as pause, escalation, or abort-safe category.
- Safe dry-run RETRY evidence indicating repeated retry would not help, if
  available.

Forbidden inputs include raw prompts, rewritten prompts, raw responses, raw
provider payloads, raw receipts, stack traces, stdout/stderr, command args,
secrets, credentials, headers, cookies, file contents, and `.env` content.

## 9. Outputs

The output is a dry-run replan plan. It is safe, bounded metadata only.

The output must not include:

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
- File contents or `.env` content.

The output must clearly state whether replan would be eligible and whether it
is blocked.

## 10. Decision/Evidence Sources

Dry-run REPLAN planning may use:

- `AutonomyController` advisory decision metadata.
- Tracker-aware policy output.
- `SmartErrorProgressTracker` scores and fingerprint ID.
- `AutonomySessionTracker` safe session counters.
- Safe dry-run RETRY plan metadata, if available.
- MemoryFacade advisory evidence, if available.
- SQLite opt-in session state metadata, if available.
- Cockpit-safe autonomy diagnostics.
- Governance pause/escalate/abort-safe metadata.

Reads must degrade safely. Missing evidence should produce a blocked or
low-confidence plan, not execution.

## 11. Replan Eligibility Rules

Replan may be eligible only when all of the following are true:

- The advisory decision is REPLAN, or the recommended decision hint is
  replan-like.
- Repeated RETRY would not help.
- `stagnation_score` is higher than `progress_score`.
- `repeated_strategy_count` suggests the same approach is stuck.
- Risk is low or medium.
- No secret is detected.
- No protected file is involved.
- No destructive operation is involved.
- Provider routing would remain unchanged.
- Runtime output would not be changed.
- The original prompt would not be rewritten.
- No provider/model call is required.
- No tool execution is required.
- No command execution is required.
- No file write is required.
- No governance pause, escalation, or abort-safe signal blocks the plan.

Eligibility does not authorize execution. It only means the plan may report
`would_replan=true`.

## 12. Replan Blocking Rules

Replan must be blocked when any of the following are true:

- Risk is high or critical.
- A secret is detected.
- A protected file is touched.
- Provider switching is required.
- Tool, write, command, or destructive action is required.
- CI or security signal is unsafe.
- There is no safe next action.
- Governance decision says pause, escalate, or abort.
- User approval is required.
- Replan would require prompt rewriting.
- Replan would require model/provider call execution.
- Required evidence is missing or corrupt in a way that prevents safe
  planning.
- Any required field would need raw prompt, rewritten prompt, response,
  provider payload, command args, file contents, or secrets.

Blocked plans must return `would_replan=false`, `blocked=true`, and safe
`block_reasons`.

## 13. Safety Gates

Every dry-run REPLAN plan must pass these gates:

- `advisory=true`.
- `plan_type=dry_run_replan`.
- No prompt rewrite can occur.
- No rewritten prompt can be generated.
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
| `plan_type` | string | Must be `dry_run_replan` |
| `advisory` | boolean | Must be `true` |
| `would_replan` | boolean | True only if eligible and not blocked |
| `replan_reason` | string | Safe bounded reason category or summary |
| `blocked` | boolean | True when replan must not be planned |
| `block_reasons` | string array | Safe bounded categories |
| `replan_eligibility_score` | number | Bounded score, implementation-defined |
| `risk_level` | string | Safe enum-like risk value |
| `source_decision` | string | Advisory decision name, such as `REPLAN` |
| `fingerprint_id` | string | Safe fingerprint ID |
| `stagnation_score` | number | Existing safe tracker score |
| `progress_score` | number | Existing safe tracker score |
| `repeated_strategy_count` | integer | Non-negative count |
| `suggested_strategy` | string | Safe bounded strategy category, not a prompt |
| `evidence_summary` | string | Sanitized bounded summary |
| `created_at` | timestamp | UTC ISO-8601 |

Example:

```json
{
  "plan_id": "dry-replan-20260627-abc123",
  "plan_type": "dry_run_replan",
  "advisory": true,
  "would_replan": true,
  "replan_reason": "retry_stagnation_detected",
  "blocked": false,
  "block_reasons": [],
  "replan_eligibility_score": 0.72,
  "risk_level": "medium",
  "source_decision": "REPLAN",
  "fingerprint_id": "fp_123",
  "stagnation_score": 5,
  "progress_score": 1,
  "repeated_strategy_count": 3,
  "suggested_strategy": "change_safe_strategy_category",
  "evidence_summary": "replan eligible from safe stagnation metadata",
  "created_at": "2026-06-27T00:00:00+00:00"
}
```

## 15. Evidence/Audit Behavior

Dry-run REPLAN plans may be recorded as safe evidence only if a future
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
- Repeated strategy count.
- Suggested safe strategy category.
- Safe evidence summary.
- Created timestamp.

Evidence must not include raw prompts, rewritten prompts, responses, provider
payloads, receipts, stack traces, stdout/stderr, command args, headers,
cookies, secrets, credentials, file contents, `.env` content, or raw database
rows.

## 16. Cockpit Visibility Proposal

Cockpit may show dry-run REPLAN plans only as read-only diagnostics.

Allowed Cockpit fields:

- Plan ID.
- Plan type.
- Advisory flag.
- Would replan.
- Blocked.
- Block reasons.
- Replan reason.
- Eligibility score.
- Risk level.
- Source decision.
- Fingerprint ID.
- Progress/stagnation scores.
- Repeated strategy count.
- Suggested strategy category.
- Created timestamp.

Cockpit must not expose a Replan button, prompt rewrite control, destructive
control, provider switch control, patch control, CI repair control, or
commit/push/PR control. Cockpit must not render raw prompts, rewritten prompts,
responses, provider payloads, stack traces, stdout/stderr, command args,
secrets, or file contents.

## 17. Runtime Behavior Guarantees

Dry-run REPLAN planning must guarantee:

- Original prompt unchanged.
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

- REPLAN advisory decision produces a dry-run plan only.
- Replan-like hint produces a dry-run plan only.
- No prompt rewrite occurs.
- No rewritten prompt appears in the plan.
- No second provider call is made.
- No model call is repeated.
- Runtime response string is unchanged.
- Provider routing is unchanged.
- Repeated RETRY would not help signal contributes to eligibility.
- `stagnation_score > progress_score` contributes to eligibility.
- Repeated strategy count contributes to eligibility.
- High/critical risk blocks replan.
- Secret detection blocks replan.
- Protected-file signal blocks replan.
- Tool/write/destructive requirement blocks replan.
- Unsafe CI/security signal blocks replan.
- Governance pause/escalate/abort blocks replan.
- User approval required blocks replan.
- Prompt rewrite requirement blocks replan.
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
5. Add optional runtime inspection attachment, if it cannot change runtime
   output, prompts, or provider routing.
6. Add read-only Cockpit display, if needed.
7. Add evidence interpretation notes before any operator-facing rollout.
8. Run focused autonomy, memory, security, and UI tests as applicable.
9. Require a separate go/no-go review before any real replan execution design.

## 20. Known Risks

- Operators may confuse `would_replan=true` with approval to rewrite prompts.
- Future wiring may accidentally produce a rewritten prompt.
- Future wiring may accidentally perform a second provider/model call.
- Eligibility scores can be over-trusted.
- Missing evidence may produce false negatives.
- Stale session state may affect planning quality.
- Suggested strategy categories may be mistaken for executable instructions.
- Future Cockpit work could accidentally add action controls.
- Evidence summaries could drift toward raw payload detail if allowlists are
  not enforced.

## 21. Open Questions

- What threshold should define repeated RETRY would not help?
- What `stagnation_score` and `progress_score` gap should be required?
- Should suggested strategy be an enum shared with existing strategy tracking?
- Should dry-run REPLAN and dry-run RETRY share a common base plan model?
- Should dry-run REPLAN plans be persisted by default or attached only to
  runtime inspection?
- Should Cockpit show blocked plans, eligible plans, or both?
- Should stale session-state indicators affect eligibility score?

## 22. Go/No-Go Checklist

| Gate | Result |
|------|--------|
| Design is documentation-only | Go |
| Dry-run REPLAN is plan-only | Go |
| No prompt rewrite allowed | Go |
| No rewritten prompt allowed | Go |
| No provider call allowed | Go |
| No repeated model call allowed | Go |
| Runtime output must remain unchanged | Go |
| Provider routing must remain unchanged | Go |
| Tool/command/file execution forbidden | Go |
| Patching/CI repair/Git automation forbidden | Go |
| Output schema is metadata-only | Go |
| Raw prompt/rewritten prompt/response/provider payload forbidden | Go |
| Cockpit proposal is read-only | Go |
| Real REPLAN execution approved | No-go |
| Real RETRY execution approved | No-go |
| SELF_REPAIR approved | No-go |
| Provider switching approved | No-go |
| CI repair approved | No-go |
| Commit/push/PR automation approved | No-go |

## 23. Final Recommendation

Proceed with a future implementation branch for dry-run REPLAN planning
contracts only.

Do not implement replan execution. Do not rewrite prompts. Do not make
provider calls. Do not repeat model calls. Do not change runtime output. Do not
change provider routing. Do not add scheduler, automatic loops, tool execution,
file writes, patching, CI repair, provider switching, self-repair, or
repository automation.

The next implementation phase should produce metadata-only dry-run plans and
tests proving that no autonomous action and no prompt rewrite can occur.

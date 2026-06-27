# Autonomy Dry-Run Retry Plan Evidence Notes

**Date:** 2026-06-27
**Branch:** `feature/autonomy-dry-run-retry-plan-evidence-notes`
**Base:** `main` after PR #440
**Status:** Documentation only
**Runtime impact:** None

## 1. Purpose

This document explains how operators and reviewers should interpret
`autonomy_evaluation.dry_run_retry_plan` evidence shown in Runtime Inspector
and the Cockpit Autonomia tab.

The evidence helps reviewers understand whether advisory rules would consider
a retry eligible, why a retry is blocked, and which safe metadata informed the
plan. It is not an execution record.

## 2. Scope

This guidance applies only to dry-run RETRY plan metadata exposed through
runtime inspection and Cockpit diagnostics.

It does not define retry execution, replan execution, provider routing,
provider calls, tool execution, file writes, patching, CI repair, commit/push
automation, PR automation, or any autonomous action path.

## 3. What Dry-Run RETRY Evidence Means

Dry-run RETRY evidence is advisory metadata produced by the dry-run retry
planner. It describes what the advisory autonomy stack would consider under
the current safe evidence snapshot.

It may show:

- Whether RETRY would be eligible under current advisory rules.
- Whether RETRY is blocked by safety or governance rules.
- Which safe reason categories explain the plan.
- Which fingerprint and tracker scores informed the plan.
- Whether any configured retry budget remains.

## 4. What Dry-Run RETRY Evidence Does NOT Mean

Dry-run RETRY evidence does not mean that a retry happened.

It also does not mean:

- A provider/model was called again.
- The response string changed.
- Provider routing changed.
- A tool, command, file write, patch, CI repair, commit, push, or PR was
  executed.
- Autonomous execution is approved.
- Human approval gates are bypassed.
- `blocked=false` authorizes a future retry.

## 5. Field-by-Field Interpretation

| Field | Interpretation |
|-------|----------------|
| `plan_id` | Safe identifier for this dry-run plan. Use it to reference the plan in review. |
| `plan_type` | Expected value is `dry_run_retry`. Any other value should be treated as unexpected. |
| `advisory` | Expected value is `true`. It confirms the plan is advisory metadata. |
| `would_retry` | Indicates advisory eligibility only. It does not mean a retry was executed. |
| `retry_reason` | Safe bounded category explaining the high-level plan result. |
| `blocked` | Indicates whether safety/governance rules block retry planning. |
| `block_reasons` | Safe bounded categories explaining why the plan is blocked. |
| `retry_eligibility_score` | Advisory score for review context only. It is not permission. |
| `risk_level` | Safe risk category used by the planner. |
| `source_decision` | Advisory autonomy decision that informed the plan, such as `RETRY`. |
| `fingerprint_id` | Safe fingerprint linking related error/progress evidence. |
| `progress_score` | Safe tracker score indicating detected progress. |
| `stagnation_score` | Safe tracker score indicating repeated or stagnant behavior. |
| `repeated_strategy_count` | Count of repeated safe strategy names, if available. |
| `max_attempts_remaining` | Advisory remaining retry budget. It is not execution approval. |
| `evidence_summary` | Sanitized bounded summary, if available. Do not expand it with raw payloads. |
| `created_at` | Timestamp when the dry-run plan metadata was created. |

## 6. How to Interpret `would_retry=true`

`would_retry=true` means "would be eligible under advisory rules."

It does not mean:

- RETRY was executed.
- A provider/model was called again.
- Runtime output changed.
- Provider routing changed.
- Autonomous execution is approved.

Treat `would_retry=true` as evidence that the current safe metadata passed the
dry-run eligibility rules. A separate future design, implementation, governance
review, and approval would still be required before any real retry execution.

## 7. How to Interpret `blocked=true`

`blocked=true` means the planner found one or more safety, risk, governance,
or evidence conditions that prevent a retry plan from being eligible.

Blocked plans should be treated as a stop signal for retry planning review.
They do not execute fallback actions. They do not invoke ABORT_SAFE,
SELF_REPAIR, SWITCH_PROVIDER, REPLAN, or RETRY.

## 8. How to Interpret `block_reasons`

`block_reasons` is a list of safe categorical reasons. Examples may include:

- `risk_too_high`
- `secret_detected`
- `protected_file_involved`
- `provider_switching_required`
- `destructive_operation_required`
- `tool_action_required`
- `write_action_required`
- `command_action_required`
- `unsafe_ci_or_security_signal`
- `no_safe_next_action`
- `max_attempts_exceeded`
- `governance_pause`
- `governance_escalate`
- `governance_abort`
- `user_approval_required`

These categories are safe to discuss in review. They should not be expanded
with raw prompts, responses, logs, traces, command arguments, provider
payloads, tool outputs, file contents, or secrets.

## 9. How to Interpret `retry_eligibility_score`

`retry_eligibility_score` is advisory evidence only.

It can help reviewers compare plans or understand planner confidence, but it is
not permission to retry. A high score does not approve autonomous execution. A
low score does not execute any fallback. A score must be interpreted alongside
`would_retry`, `blocked`, `block_reasons`, `risk_level`, and governance state.

## 10. How to Interpret `fingerprint_id`

`fingerprint_id` is a safe identifier for related error/progress evidence.

Use it to correlate repeated failures, stagnation, or progress patterns across
diagnostics. It is not a raw stack trace, raw receipt, raw prompt, raw response,
or provider payload. If a fingerprint is missing, stale, or unexpected, treat
the plan as lower confidence and verify surrounding diagnostics.

## 11. How to Interpret Progress/Stagnation Scores

`progress_score` indicates safe evidence that the runtime state is moving in a
better direction. `stagnation_score` indicates repeated or stuck behavior.

These scores are review signals. They do not change runtime output, route
providers, execute retries, or approve follow-up actions. High stagnation may
support retry eligibility only when all safety gates also pass.

## 12. How to Interpret `max_attempts_remaining`

`max_attempts_remaining` is the advisory retry budget remaining under the
planner's safe context. A value greater than zero does not approve execution.
A value of zero should block retry planning with a max-attempts reason.

This value should be reviewed with the session state, risk level, and
governance state before any future phase considers real retry execution.

## 13. What Evidence Can Be Shared in Review

The following dry-run RETRY fields are safe to paste into review or audit
notes when they appear exactly as sanitized metadata:

- `plan_id`
- `plan_type`
- `advisory`
- `would_retry`
- `blocked`
- `block_reasons`
- `retry_eligibility_score`
- `risk_level`
- `source_decision`
- `fingerprint_id`
- `progress_score`
- `stagnation_score`
- `repeated_strategy_count`
- `max_attempts_remaining`
- `created_at`

Include `evidence_summary` only if it is already sanitized and bounded, and
only when it does not contain raw prompt, raw response, payload, logs, traces,
file contents, command arguments, or secrets.

## 14. What Evidence Must Never Be Shared

Do not paste or share:

- Raw prompt.
- Raw response.
- Provider payload.
- Provider credentials.
- API keys, tokens, or secrets.
- Stack traces or tracebacks.
- stdout/stderr.
- Command args.
- File contents.
- `.env` content.
- Full tool outputs.
- Raw receipts.
- Raw database rows.
- Raw session state dumps.
- Headers or cookies.

If a review requires deeper debugging, capture a new sanitized diagnostic
summary instead of copying raw runtime material.

## 15. Cockpit Interpretation Notes

The Cockpit Autonomia tab displays the dry-run RETRY plan as read-only
diagnostics with the label:

`Plano dry-run somente leitura - nenhum retry executado.`

Operators should read the panel as a planning summary, not a control surface.
The Cockpit must not expose Retry buttons, provider-switch buttons, patch
controls, CI repair controls, commit/push controls, PR controls, or any
destructive action tied to the plan.

Missing plan metadata should be interpreted as "no dry-run retry plan
available," not as approval or denial.

## 16. Operator Checklist

Before referencing dry-run RETRY evidence in review:

- Confirm the panel says no retry was executed.
- Confirm `plan_type` is `dry_run_retry`.
- Confirm `advisory` is `true`.
- Check `would_retry`, `blocked`, and `block_reasons` together.
- Check `risk_level` before interpreting eligibility.
- Check `source_decision` and `fingerprint_id` for correlation.
- Check progress and stagnation scores for context.
- Check `max_attempts_remaining` for budget context.
- Share only safe checklist fields.
- Do not paste raw runtime data, provider payloads, logs, command args, file
  contents, receipts, or secrets.

## 17. Security Considerations

Dry-run RETRY evidence must remain metadata-only. Any evidence copied into
issues, PRs, audit notes, chat, or external systems should be sanitized first.

The safe plan fields are not a substitute for security review. If
`secret_detected`, `protected_file_involved`, `unsafe_ci_or_security_signal`,
or any governance blocker appears, treat the plan as blocked and escalate
through the existing manual review process.

Do not use dry-run evidence to infer provider credentials, reconstruct prompts,
reconstruct responses, or expose file contents.

## 18. Known Risks

- Operators may confuse `would_retry=true` with a completed retry.
- Operators may over-trust `retry_eligibility_score`.
- `blocked=false` may be misread as permission for autonomous execution.
- Missing or stale session evidence can make a plan incomplete.
- A safe `fingerprint_id` can correlate events but does not prove full root
  cause.
- Future UI changes could accidentally add action controls if the read-only
  boundary is not maintained.
- Evidence summaries could drift toward raw payload detail if allowlists are
  weakened.

## 19. Future Improvements

Potential future work, each requiring a separate approved branch:

- Add a compact review-export format containing only safe checklist fields.
- Add explicit "stale evidence" indicators if session state age is available.
- Add confidence categories separate from `retry_eligibility_score`.
- Add dry-run REPLAN evidence notes with a shared interpretation model.
- Add tests that verify exported evidence never includes forbidden raw fields.
- Add governance review gates before any real RETRY execution design.

## 20. Final Warning

Dry-run RETRY does not execute a retry. It does not call the provider/model
again. It does not change the response string. It does not change provider
routing. It does not execute tools, commands, file writes, patches, CI repair,
commits, pushes, or PRs.

`would_retry=true` means "would be eligible under advisory rules," not "retry
was executed." `blocked=false` does not approve autonomous execution.
`retry_eligibility_score` is advisory evidence, not permission.

Omni is still not approved for autonomous execution.

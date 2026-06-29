# Autonomy Dry-Run Replan Plan Evidence Notes

**Date:** 2026-06-28
**Branch:** `feature/autonomy-dry-run-replan-plan-evidence-notes`
**Base:** `main` after PR #444
**Status:** Documentation only
**Runtime impact:** None

## 1. Purpose

This document explains how operators and reviewers should interpret
`autonomy_evaluation.dry_run_replan_plan` evidence shown in Runtime Inspector
and the Cockpit Autonomia tab.

The evidence helps reviewers understand whether advisory rules would consider a
future replan eligible, why a replan is blocked, and which safe metadata
informed the plan. It is not an execution record.

## 2. Scope

This guidance applies only to dry-run REPLAN plan metadata exposed through
runtime inspection and Cockpit diagnostics.

It does not define prompt rewriting, replan execution, retry execution,
provider routing, provider calls, tool execution, command execution, file
writes, patching, CI repair, commit/push automation, PR automation, provider
switching, self-repair, or any autonomous action path.

## 3. What Dry-Run REPLAN Evidence Means

Dry-run REPLAN evidence is advisory metadata produced by the dry-run replan
planner. It describes what the advisory autonomy stack would consider under
the current safe evidence snapshot.

It may show:

- Whether REPLAN would be eligible under current advisory rules.
- Whether REPLAN is blocked by safety or governance rules.
- Which safe reason categories explain the plan.
- Which fingerprint and tracker scores informed the plan.
- Whether repeated retry appears not useful.
- Whether repeated strategy evidence suggests the current approach is stuck.
- Which safe strategy category might be considered later.

## 4. What Dry-Run REPLAN Evidence Does NOT Mean

Dry-run REPLAN evidence does not mean that a replan happened.

It also does not mean:

- A prompt was rewritten.
- A rewritten prompt was generated.
- A retry was executed.
- A provider/model was called again.
- The response string changed.
- Provider routing changed.
- A tool, command, file write, patch, CI repair, commit, push, or PR was
  executed.
- Autonomous execution is approved.
- Human approval gates are bypassed.
- `blocked=false` authorizes a future replan.

## 5. Field-by-Field Interpretation

| Field | Interpretation |
|-------|----------------|
| `plan_id` | Safe identifier for this dry-run plan. Use it to reference the plan in review. |
| `plan_type` | Expected value is `dry_run_replan`. Any other value should be treated as unexpected. |
| `advisory` | Expected value is `true`. It confirms the plan is advisory metadata. |
| `would_replan` | Indicates advisory eligibility only. It does not mean a replan was executed. |
| `replan_reason` | Safe bounded category explaining the high-level plan result. |
| `blocked` | Indicates whether safety/governance rules block replan planning. |
| `block_reasons` | Safe bounded categories explaining why the plan is blocked. |
| `replan_eligibility_score` | Advisory score for review context only. It is not permission. |
| `risk_level` | Safe risk category used by the planner. |
| `source_decision` | Advisory autonomy decision that informed the plan, such as `REPLAN`. |
| `fingerprint_id` | Safe fingerprint linking related error/progress evidence. |
| `progress_score` | Safe tracker score indicating detected progress. |
| `stagnation_score` | Safe tracker score indicating repeated or stagnant behavior. |
| `repeated_strategy_count` | Count of repeated safe strategy names, if available. |
| `suggested_strategy` | Safe categorical metadata only. It is not an executable instruction. |
| `evidence_summary` | Sanitized bounded summary, if available. Do not expand it with raw payloads. |
| `created_at` | Timestamp when the dry-run plan metadata was created. |

## 6. How to Interpret `would_replan=true`

`would_replan=true` means "would be eligible under advisory rules."

It does not mean:

- REPLAN was executed.
- A prompt was rewritten.
- A provider/model was called again.
- Runtime output changed.
- Provider routing changed.
- Autonomous execution is approved.

Treat `would_replan=true` as evidence that the current safe metadata passed the
dry-run eligibility rules. A separate future design, implementation,
governance review, and approval would still be required before any real replan
execution.

## 7. How to Interpret `blocked=true`

`blocked=true` means the planner found one or more safety, risk, governance,
or evidence conditions that prevent a replan plan from being eligible.

Blocked plans should be treated as a stop signal for replan planning review.
They do not execute fallback actions. They do not invoke ABORT_SAFE,
SELF_REPAIR, SWITCH_PROVIDER, RETRY, or REPLAN.

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
- `retry_still_useful`
- `stagnation_not_dominant`
- `strategy_not_stuck`
- `governance_pause`
- `governance_escalate`
- `governance_abort`
- `user_approval_required`
- `prompt_rewrite_required`
- `model_or_provider_call_required`

These categories are safe to discuss in review. They should not be expanded
with raw prompts, rewritten prompts, responses, logs, traces, command
arguments, provider payloads, tool outputs, file contents, or secrets.

## 9. How to Interpret `replan_eligibility_score`

`replan_eligibility_score` is advisory evidence only.

It can help reviewers compare plans or understand planner confidence, but it
is not permission to replan. A high score does not approve autonomous
execution. A low score does not execute any fallback. A score must be
interpreted alongside `would_replan`, `blocked`, `block_reasons`, `risk_level`,
`suggested_strategy`, and governance state.

## 10. How to Interpret `suggested_strategy`

`suggested_strategy` is safe categorical metadata only.

It may indicate the type of future strategy category the planner would
consider, such as `change_safe_strategy_category`. It must not be treated as a
prompt rewrite, a new prompt, an executable instruction, a tool instruction, a
command, a patch plan, or permission to perform a replan.

Operators may share the category in review, but must not add raw prompt text,
rewritten prompt text, command details, file contents, provider payloads, or
secrets to explain it.

## 11. How to Interpret `fingerprint_id`

`fingerprint_id` is a safe identifier for related error/progress evidence.

Use it to correlate repeated failures, stagnation, or progress patterns across
diagnostics. It is not a raw stack trace, raw receipt, raw prompt, rewritten
prompt, raw response, or provider payload. If a fingerprint is missing, stale,
or unexpected, treat the plan as lower confidence and verify surrounding
diagnostics.

## 12. How to Interpret Progress/Stagnation Scores

`progress_score` indicates safe evidence that the runtime state is moving in a
better direction. `stagnation_score` indicates repeated or stuck behavior.

For dry-run REPLAN, a higher `stagnation_score` than `progress_score` may
support eligibility only when repeated retry appears not useful, repeated
strategy evidence suggests the current approach is stuck, and all safety gates
also pass.

These scores are review signals. They do not change runtime output, rewrite
prompts, route providers, execute replans, or approve follow-up actions.

## 13. What Evidence Can Be Shared in Review

The following dry-run REPLAN fields are safe to paste into review or audit
notes when they appear exactly as sanitized metadata:

- `plan_id`
- `plan_type`
- `advisory`
- `would_replan`
- `blocked`
- `block_reasons`
- `replan_eligibility_score`
- `risk_level`
- `source_decision`
- `fingerprint_id`
- `progress_score`
- `stagnation_score`
- `repeated_strategy_count`
- `suggested_strategy`
- `created_at`

Include `evidence_summary` only if it is already sanitized and bounded, and
only when it does not contain raw prompt, rewritten prompt, raw response,
payload, logs, traces, file contents, command arguments, tool outputs,
receipts, or secrets.

## 14. What Evidence Must Never Be Shared

Do not paste or share:

- Raw prompt.
- Rewritten prompt.
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

The Cockpit Autonomia tab displays the dry-run REPLAN plan as read-only
diagnostics with the label:

`Plano dry-run somente leitura - nenhum replan executado.`

Operators should read the panel as a planning summary, not a control surface.
The Cockpit must not expose Replan buttons, Retry buttons, provider-switch
buttons, patch controls, CI repair controls, commit/push controls, PR controls,
or any destructive action tied to the plan.

Missing plan metadata should be interpreted as "no dry-run replan plan
available," not as approval or denial.

## 16. Operator Checklist

Before referencing dry-run REPLAN evidence in review:

- Confirm the panel says no replan was executed.
- Confirm `plan_type` is `dry_run_replan`.
- Confirm `advisory` is `true`.
- Check `would_replan`, `blocked`, and `block_reasons` together.
- Check `risk_level` before interpreting eligibility.
- Check `source_decision` and `fingerprint_id` for correlation.
- Check progress and stagnation scores for context.
- Check `repeated_strategy_count` for repeated strategy context.
- Confirm `suggested_strategy` is a safe category only.
- Share only safe checklist fields.
- Do not paste raw runtime data, rewritten prompts, provider payloads, logs,
  command args, file contents, receipts, full tool outputs, or secrets.

## 17. Security Considerations

Dry-run REPLAN evidence must remain metadata-only. Any evidence copied into
issues, PRs, audit notes, chat, or external systems should be sanitized first.

The safe plan fields are not a substitute for security review. If
`secret_detected`, `protected_file_involved`, `unsafe_ci_or_security_signal`,
`prompt_rewrite_required`, `model_or_provider_call_required`, or any
governance blocker appears, treat the plan as blocked and escalate through the
existing manual review process.

Do not use dry-run evidence to infer provider credentials, reconstruct prompts,
reconstruct responses, reconstruct provider payloads, expose file contents, or
derive executable instructions.

## 18. Known Risks

- Operators may confuse `would_replan=true` with a completed replan.
- Operators may over-trust `replan_eligibility_score`.
- Operators may misread `suggested_strategy` as an instruction.
- `blocked=false` may be misread as permission for autonomous execution.
- A stale `fingerprint_id` may make evidence correlation misleading.
- Progress and stagnation scores may be misunderstood without surrounding
  runtime context.
- Evidence summaries may be copied with unsafe raw context added manually.

## 19. Future Improvements

Future work may add:

- A dedicated dry-run REPLAN evidence checklist in Cockpit.
- Safer copy-to-review formatting that includes only approved fields.
- More explicit stale-fingerprint indicators.
- Operator guidance that compares dry-run RETRY and dry-run REPLAN evidence.
- A separate go/no-go review before any real replan execution design.

None of these improvements should add prompt rewriting, provider/model calls,
runtime response mutation, provider routing changes, tool execution, command
execution, file writes, patching, CI repair, commit/push/PR automation,
provider switching, self-repair, or scheduler behavior without a separate
approved design.

## 20. Final Warning

Dry-run REPLAN does not rewrite prompts. Dry-run REPLAN does not execute a
replan. Dry-run REPLAN does not execute a retry. Dry-run REPLAN does not call
the provider/model again. Dry-run REPLAN does not change the response string.
Dry-run REPLAN does not change provider routing. Dry-run REPLAN does not
execute tools, commands, file writes, patches, CI repair, commits, pushes, or
PRs.

`would_replan=true` means "would be eligible under advisory rules," not
"replan was executed." `blocked=false` does not approve autonomous execution.
`replan_eligibility_score` is advisory evidence, not permission.
`suggested_strategy` is categorical metadata only, not an executable
instruction.

Omni is still not approved for autonomous execution.

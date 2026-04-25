# Learning Debugging

## Goal

Omni now records a safe learning record for each turn so contributors can inspect decision quality without modifying the system.

## Where Records Are Stored

Local files:

- `.logs/fusion-runtime/learning/controlled/learning_records.jsonl`
- `.logs/fusion-runtime/learning/controlled/improvement_signals.jsonl`

These files are local debug artifacts. They are not meant to be committed.

## What To Inspect

Important fields in a learning record:

- `selected_strategy`
- `selected_tool`
- `execution_path`
- `runtime_mode`
- `success`
- `failure_class`
- `decision_evaluation.decision_correct`
- `decision_evaluation.decision_issue`
- `execution_outcome.tool_used`
- `execution_outcome.tool_failed`
- `execution_outcome.fallback_triggered`

## How To Identify A Bad Decision

Typical bad-decision patterns:

- `tool_required_but_not_used`
- `fallback_misuse`
- `compatibility_used_when_execution_required`
- `wrong_tool`
- `tool_execution_failed`

Interpretation:

- decision issue present:
  - the routing or execution choice should be reviewed
- `decision_correct=true`:
  - the current rule set considers the turn acceptable
- `decision_correct=null`:
  - the turn needs manual review

## Runtime Debug Surface

The runtime inspection now exposes:

- `learning_record_created`
- `decision_correct`
- `decision_issue`
- `phase10_learning_record`
- `phase10_improvement_signals`

This allows contributors to inspect decision quality without opening backend logs first.

## How Contributors Can Help

Useful contributions:

- tighten deterministic routing for repeated bad-decision patterns
- improve tool selection rules
- improve failure classification
- add new high-quality decision dataset cases
- reduce fallback where a deterministic execution path is clearly available

Do not:

- add auto-self-modification
- auto-apply improvement signals
- use learning records to mutate runtime logic directly

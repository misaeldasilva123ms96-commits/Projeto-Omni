# Learning Loop

Omni now records a bounded learning record for each completed turn without modifying itself.

## Purpose

The learning loop exists to answer four questions after a turn finishes:

- what decision was made
- what execution path actually happened
- whether the decision appears correct
- what improvement should be suggested for later review

This is an observability and analysis layer. It is not an auto-mutation system.

## What Is Recorded

Each controlled learning record stores:

- sanitized input preview
- input hash
- selected strategy
- selected tool
- execution path
- runtime mode
- success or failure
- failure class
- provider used
- decision evaluation
- execution outcome

The record is intentionally bounded and sanitized. It does not store raw secrets or unbounded conversation history.

## Decision Evaluation

The current evaluation rules are deterministic:

- if a tool was required and no tool was used, the decision is bad
- if fallback was used when execution was expected, the decision is bad
- if compatibility execution remained active for a must-execute turn, the decision is bad
- if the wrong tool was selected, the decision is bad
- if the tool runtime failed, the decision is marked as execution failure
- if the turn completed successfully, the decision is marked correct

These rules are intentionally simple. They create auditable signals before any future learning-policy refinement.

## Improvement Signals

Improvement signals are advisory only.

Examples:

- `ROUTING_IMPROVEMENT`
- `FALLBACK_REDUCTION`
- `EXECUTION_PROMOTION`
- `TOOL_SELECTION_IMPROVEMENT`
- `TOOL_RUNTIME_IMPROVEMENT`

Each signal contains:

- type
- pattern
- suggestion
- confidence
- evidence summary

No signal is applied automatically.

## Storage

Storage is local and append-only:

- records: `.logs/fusion-runtime/learning/controlled/learning_records.jsonl`
- improvement signals: `.logs/fusion-runtime/learning/controlled/improvement_signals.jsonl`

The store supports:

- append
- recent reads
- filtering by failure class, decision issue, or tool used
- grouped counts

## Integration Point

The orchestrator records the controlled learning record after execution and after runtime inspection is available.

This means the logger can capture:

- selected strategy
- execution path used
- tool diagnostics
- runtime mode
- fallback state
- provider diagnostics
- structured inspection signals

## Safety

This system is safe because:

- it does not change runtime behavior automatically
- it does not apply patches or mutate routing rules
- it stores sanitized previews, not raw secrets
- it generates advisory signals only

The learning loop supports human-guided improvement, not autonomous self-modification.

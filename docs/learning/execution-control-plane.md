# Execution Control Plane

## Why Phase 4 exists

Before Phase 4, the Omni runtime selected strategies and produced manifests, but the actual execution path was still largely implicit inside the orchestrator.

Phase 4 introduces a control plane so that:

- strategy selection maps to explicit executors
- execution decisions stay auditable
- governance signals remain authoritative
- fallback stays conservative

## Main components

- `strategy_models.py`
- `strategy_executor_base.py`
- `strategy_executors/`
- `strategy_dispatcher.py`
- `response_synthesis.py`

## Observability

The control plane emits execution-oriented events and summaries such as:

- strategy dispatch applied
- executor used
- execution status
- manifest-driven execution
- governance downgrade applied
- fallback and blocked paths

## Feedback into training

`omni-training` now extracts execution examples from runtime logs so weighted SFT datasets can learn from:

- selected strategy
- executor used
- execution status
- fallback occurrence
- ambiguity context

## Current limits

The dispatcher still wraps the compatibility execution path for most real work. That is intentional in this phase to keep the rollout reversible and prevent regressions.

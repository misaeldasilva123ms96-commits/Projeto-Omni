# Agent Negotiation Model

> Historical configuration note: Any `OMINI_*` names below are preserved only as immutable audit evidence. They are obsolete and are not accepted by the current runtime, which recognizes only `OMNI_*` configuration.

## Flow
- proposal
- counterproposal
- evaluation
- critic review
- final orchestrator decision

## Participants
- planner
- researcher
- reviewer
- critic
- simulator

## Boundaries
- negotiation is bounded by `OMINI_NEGOTIATION_MAX_DEPTH`
- the orchestrator keeps final authority
- disagreements are persisted, not hidden

## Observability
- event: `runtime.negotiation.summary`
- checkpoint field: `negotiation_summary`
- operator inspection: `inspect_negotiation(run_id)`

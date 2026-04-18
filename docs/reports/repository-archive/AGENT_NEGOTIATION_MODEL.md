# Agent Negotiation Model

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

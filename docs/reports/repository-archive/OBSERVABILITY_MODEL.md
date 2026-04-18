# Observability Model

## Goal

The observability model exists to make real agent behavior debuggable and operationally understandable across planning, execution, correction, checkpointing, and resume.

## Event Taxonomy

The live runtime now emits or persists evidence for:

- runtime mode selection
- semantic retrieval
- vector retrieval
- specialist-assisted planning
- critic review
- graph plan creation
- parallel scheduling
- step execution
- evaluator outcome
- correction attempt
- checkpoint creation
- checkpoint validation
- stale checkpoint blocking
- run resume
- final completion
- blocked or failed completion
- cooperative planning
- branch start/complete/decision
- simulation review
- run intelligence summaries

## Correlation Identity

The runtime now correlates activity through:

- `user_id`
- `session_id`
- `task_id`
- `run_id`
- step/action index
- `branch_id`
- `shared_goal_id`

These IDs make it possible to reconstruct what happened during a task instead of relying on a single final answer string.

## Audit Schema

Primary audit store:

- `.logs/fusion-runtime/execution-audit.jsonl`

Current records may include:

- `event_type`
- `user_id`
- `session_id`
- `task_id`
- `run_id`
- runtime mode
- semantic retrieval metadata
- graph metadata
- critic metadata
- action payload
- result payload
- evaluator outcome
- correction events
- timestamps

## Transcript Model

Transcript persistence remains append-only and conversation-linked, but now multi-step runtime behavior can also be correlated back to:

- checkpoint files
- runtime audit entries
- memory updates

This is important because the final response is only one artifact of the run.

## Checkpoint Observability

Checkpoint storage:

- `.logs/fusion-runtime/checkpoints/`

Checkpoint state makes the following visible:

- what already completed
- what remains to run
- whether the run blocked or finished
- where resume will continue

## Semantic Retrieval Observability

Semantic retrieval is now visible through:

- semantic query storage in runtime memory
- last semantic matches in memory envelopes
- semantic retrieval metadata attached to execution requests/audits
- `runtime.vector.retrieval` audit events

This makes it possible to explain why the runtime selected a given artifact.

## Correction And Delegation Visibility

The runtime now records:

- correction attempts
- reason codes for retry/revise/stop
- evaluator summaries at the step level
- critic review outputs for risky plans and weak steps
- graph/parallel scheduling decisions

Delegation remains under the main orchestrator, and specialist participation is visible through the planning/evaluation path rather than hidden inside a fake single-step answer.

## Failure Classification

The current model distinguishes among:

- permission block
- retryable runtime failure
- timeout from the Rust bridge
- missing artifact/path recoverable revision
- exhausted retry budget
- stale checkpoint
- checkpoint signature mismatch
- completed with warnings

## Phase 5 Event Types

New Phase 5 event types include:

- `runtime.vector.retrieval`
- `runtime.critic.plan`
- `runtime.graph.plan`
- `runtime.parallel.start`
- `runtime.checkpoint.resume_blocked`

## Phase 7 Event Types

- `runtime.cooperation.plan`
- `runtime.branch.start`
- `runtime.branch.complete`
- `runtime.branch.decision`
- `runtime.simulation.review`
- `runtime.run.summary`

## Phase 8 Event Types

- `runtime.negotiation.summary`
- `runtime.strategy.optimization`
- `runtime.supervision.alert`

## Execution State Visibility

Phase 8 also exposes machine-readable runtime state through:

- checkpointed `execution_tree`
- run summary `execution_state`
- operator inspection payloads for negotiation and supervision
- correlated branch, contribution, simulation, and strategy metadata

## Operational Value

This observability model is intended to support:

- runtime debugging
- task/run inspection APIs
- future dashboards
- safer operational review of correction loops and semantic retrieval behavior

## Next Improvements

1. summarize metrics across runs
2. add retention and compaction policy
3. expose audit inspection through an API boundary
4. track specialist-level performance trends

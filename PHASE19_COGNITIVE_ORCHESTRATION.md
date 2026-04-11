# Phase 19 - Cognitive Orchestration Layer

## Mission

Phase 19 introduces a bounded cognitive orchestration layer that coordinates runtime capabilities and execution routes using planning state, continuation decisions, learning signals, and recent execution artifacts.

This phase does not introduce unconstrained autonomy. It introduces an explicit, inspectable routing layer that helps Omni choose how execution should proceed while preserving the authority of safety and continuation controls.

## Architecture

The orchestration layer lives in `backend/python/brain/runtime/orchestration/`:

- `models.py`
  - typed context, capability, decision, conflict resolution, result, and policy models
- `context_builder.py`
  - builds unified orchestration context from plan state, checkpoint, summary, receipts, and learning signals
- `capability_registry.py`
  - explicit registry of available runtime capabilities and metadata
- `orchestration_policy.py`
  - deterministic, environment-driven orchestration policy defaults
- `route_selector.py`
  - bounded route selection engine
- `conflict_resolver.py`
  - deterministic priority resolution between continuation and learning hints
- `result_synthesizer.py`
  - merges orchestration outputs into a unified operational result without losing artifacts
- `orchestration_store.py`
  - persists contexts, decisions, routes, and synthesized results
- `orchestration_executor.py`
  - coordinates the orchestration lifecycle

## Context Model

`OrchestrationContext` collects:

- plan id and plan status
- current step id and current step status
- continuation decision type
- latest checkpoint id and status
- operational summary payload
- current action metadata
- recent execution receipt ids
- recent repair receipt ids
- advisory learning signals

The context is compact and deterministic so later phases can inspect orchestration history without reconstructing it from raw logs.

## Capability Registry

The capability registry is explicit and inspectable. Phase 19 includes:

- `planning_execution`
- `repair_workflow`
- `continuation_management`
- `engineering_tool_execution`
- `rust_bridge_execution`
- `memory_access`
- `analysis_routine`

Each capability records:

- subsystem
- supported action types
- priority level
- confidence score
- failure risk

## Routing Model

Current bounded routes are:

- `direct_execution`
- `repair_attempt`
- `retry_execution`
- `plan_rebuild`
- `analysis_step`
- `tool_delegation`
- `pause_plan`
- `escalate_failure`
- `complete_plan`

Routing rules are deterministic. Examples:

- read-heavy filesystem actions prefer `analysis_step`
- engineering tools prefer `tool_delegation`
- continuation `retry_step` maps to `retry_execution`
- continuation `rebuild_plan` maps to `plan_rebuild`
- continuation pause, escalation, and completion remain authoritative

## Conflict Resolution

Signals may disagree. Phase 19 resolves conflicts in this order:

1. execution safety
2. policy constraints
3. continuation decision
4. learning signals

This means advisory learning hints can enrich confidence and traceability, but they do not silently override continuation lifecycle control.

## Result Synthesis

`ResultSynthesizer` preserves:

- route selected
- selected capability
- reason summary
- execution receipt references
- repair receipt references
- checkpoint references
- primary result payload

The orchestration result becomes a compact operational artifact instead of a lossy summary.

## Integration Points

Phase 19 integrates conservatively with existing layers:

- before action execution, the orchestrator records a pre-execution orchestration artifact
- after continuation decisions, the orchestrator records a post-decision orchestration artifact
- trusted execution remains the only execution wrapper
- self-repair policy remains intact
- continuation remains authoritative for lifecycle control
- learning signals stay advisory

## Persistence

Artifacts are stored under:

- `.logs/fusion-runtime/orchestration/context/`
- `.logs/fusion-runtime/orchestration/decisions/`
- `.logs/fusion-runtime/orchestration/routes/`
- `.logs/fusion-runtime/orchestration/results/`

All files are JSONL and remain compact and auditable.

## Policy Defaults

Phase 19 defaults are conservative:

- `OMINI_ORCHESTRATION_ALLOW_TOOL_DELEGATION=true`
- `OMINI_ORCHESTRATION_ALLOW_ANALYSIS_ROUTING=true`
- `OMINI_ORCHESTRATION_ALLOW_LEARNING_HINTS=true`
- `OMINI_ORCHESTRATION_MAX_LEARNING_WEIGHT=0.25`

## Limitations

Phase 19 intentionally does not implement:

- dynamic capability creation
- unrestricted multi-agent routing
- silent continuation overrides
- bypass of trusted execution
- self-modifying orchestration policy

This layer is still bounded operational orchestration.

## How This Prepares Phase 20

Phase 19 provides the routing substrate needed for a future higher-level coordination phase:

- contexts are now unified across planning, continuation, repair, and learning
- route choices are explicit and persisted
- downstream orchestration can now reason from a structured history of capability selections and route outcomes

Phase 20 can build richer system-level coordination on top of these artifacts while preserving deterministic governance and auditability.

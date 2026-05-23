# Phase 37 — Multi-Agent Coordination System

## Scope (implemented)

Phase 37 adds a **governed, auditable coordination layer** between **planning intelligence** and **execution / swarm boundary** on the main `BrainOrchestrator.run` chat path.

- **`AgentCoordinator`** (`brain.runtime.coordination`): selects a fixed bounded sequence of runtime specialist roles — **planner → executor → validator → critic** — implemented as **structured transforms** (no new LLM personas, no autonomous decomposition).
- **`CoordinationState`**: per-turn bounded record (session, plan, memory/strategy trace refs, control summary mirrors) with accumulated specialist notes (capped).
- **`CoordinationResult`**: `trace` (`MultiAgentCoordinationTrace`) + `handoff_bundle` merged into the **swarm `context_session`** under `multi_agent_coordination` after Phase 36 performance shaping.
- **Observability**: audit event `runtime.multi_agent_coordination.trace` (flattened `trace` + `handoff_bundle` in JSONL, consistent with other runtime traces). Readers: `read_recent_multi_agent_coordination_traces` / `read_latest_multi_agent_coordination_trace`; snapshot fields on `ObservabilitySnapshot`.

## Authority hierarchy (preserved)

1. Control / governance — allow or block execution (orchestrator; unchanged).
2. Reasoning — intent and handoff.
3. Planning — execution plan structure.
4. **Coordination** — advisory specialist ordering, readiness labels, digest for Node/swarm.
5. Specialists **do not** override control-plane decisions, approve forbidden execution, or mutate blocked outcomes.

`execution_readiness` values such as `advisory_review` or `ready_with_risk_signals` are **non-blocking hints** unless existing control semantics already block.

## Distinction from existing `SpecialistCoordinator`

`brain.runtime.specialists.SpecialistCoordinator` remains the **goal / action / simulation** path. Phase 37 **`AgentCoordinator`** is dedicated to the **chat pipeline** between plan and swarm, avoiding replacement of that subsystem.

## Phase 38+ (not implemented)

- **Phase 38** — autonomous task decomposition, open-ended subproblem expansion.
- **Phase 39+** — self-evolution, distributed scheduling, unconstrained agent dialogues.

## Tests

`tests/runtime/coordination/test_agent_coordinator.py` covers role order, skipped direct-memory path, blocked control branch, validator/critic propagation, and degraded fallback.

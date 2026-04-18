# System overview

Omni is a **governed cognitive runtime**: a Python orchestrator coordinates planning, execution, memory, learning, strategy, performance, multi-agent coordination, decomposition, and **bounded evolution** with explicit validation, rollout, and rollback. A Rust boundary and Node runtime integrate behind stable contracts.

## High-level flow

```text
Input
  → OIL normalization (typed runtime I/O)
  → Memory + reasoning + planning
  → Strategy + performance + coordination + decomposition
  → Execution (governed tools / bridges)
  → Learning + traces
  → Controlled evolution (Phase 39) + improvement orchestration (Phase 40)
```

## Source-of-truth map

| Concern | Primary code |
|--------|----------------|
| Orchestration | `backend/python/brain/runtime/orchestrator.py` |
| Governance / runs | `backend/python/brain/runtime/control/` |
| Reasoning | `backend/python/brain/runtime/reasoning/` |
| Memory | `backend/python/brain/runtime/memory/` |
| Planning | `backend/python/brain/runtime/planning/` |
| Learning | `backend/python/brain/runtime/learning/` |
| Strategy | `backend/python/brain/runtime/strategy/` |
| Performance | `backend/python/brain/runtime/performance/` |
| Coordination | `backend/python/brain/runtime/coordination/` |
| Decomposition | `backend/python/brain/runtime/decomposition/` |
| Evolution (governed) | `backend/python/brain/runtime/evolution/` |
| Improvement (Phase 40) | `backend/python/brain/runtime/improvement/` |
| Observability | `backend/python/brain/runtime/observability/` |

## Related documents

- [runtime.md](runtime.md) — orchestrator-centric view
- [orchestration.md](orchestration.md) — planning and execution routing
- [OMNI_COGNITIVE_CONTROL_LAYER.md](OMNI_COGNITIVE_CONTROL_LAYER.md) — control layer deep dive
- [OMNI_AGENT_POLICIES.md](OMNI_AGENT_POLICIES.md) — agent policy surface
- [SUPABASE_OMNI_SCHEMA.md](SUPABASE_OMNI_SCHEMA.md) — optional data plane schema notes

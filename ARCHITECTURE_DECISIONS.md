# Architecture Decisions

## ADR-001: TypeScript QueryEngine Is The Main Brain

- Context: `src.zip` contains the strongest orchestration, session, and tool-routing logic.
- Alternatives: keep Python as the main brain; keep the lightweight JS adapter as the brain.
- Decision: select the TypeScript QueryEngine lineage as the single cognitive authority.
- Consequences: the repository needs a packaging path for upstream TypeScript brain modules.

## ADR-002: Rust Owns Execution Authority

- Context: `claw-code-main.zip` has a mature permissioned execution loop and usage-aware runtime.
- Alternatives: let Python execute tools; let Node execute tools directly without a permissioned runtime.
- Decision: Rust is the long-term execution authority.
- Consequences: tool execution contracts and permission semantics must be designed around Rust first.

## ADR-003: Provider Abstraction Must Stay Outside Cognition

- Context: OpenClaude includes strong provider bootstrap and routing patterns.
- Alternatives: mix provider logic into the brain; let each subagent choose providers independently.
- Decision: provider routing lives under `platform/providers`.
- Consequences: cognition stays portable and testable.

## ADR-004: Kairos Is Deferred And Optional

- Context: proactive and scheduled layers exist upstream, but the core execution path is still stabilizing.
- Alternatives: integrate Kairos immediately; drop Kairos entirely.
- Decision: keep Kairos isolated under `features/kairos`.
- Consequences: no proactive behavior enters the critical runtime path prematurely.

## ADR-005: The Existing Adapter Becomes A Shim

- Context: the active runner imports `src/queryEngineRunnerAdapter.js`.
- Alternatives: replace the runner contract; fork a second adapter path.
- Decision: preserve the same entrypoint and route it into the new fusion brain facade.
- Consequences: zero external integration breakage while internal architecture improves.

## ADR-006: Extracted QueryEngine Kernel Is The Active Brain Authority

- Context: the full upstream `src.zip` `QueryEngine.ts` is the correct architectural source of truth, but it is tightly coupled to Bun/Ink/UI startup concerns.
- Alternatives: keep the phase-1 heuristic brain; attempt a risky full direct import of the upstream UI-bound engine.
- Decision: install an extracted QueryEngine-style authority in `core/brain/queryEngineAuthority.js` and make `fusionBrain.js` a facade only.
- Consequences: the project now has one real brain authority while preserving a safe migration path toward deeper upstream adoption.

## ADR-007: Python Hosts The Active Bridge Between Node Brain And Rust Executor

- Context: this Windows environment blocks direct Node child-process execution for the Rust bridge.
- Alternatives: keep Node as the direct executor caller; move execution authority out of Rust.
- Decision: keep the brain in Node, but route live execution requests through Python into the Rust bridge.
- Consequences: the architecture stays intact, Rust remains execution authority, and the bridge boundary is honest and testable.

## ADR-008: Memory Must Participate In Planning And Post-Execution Updates

- Context: phase 1 created memory scaffolding but it was not fully wired into the live action loop.
- Alternatives: keep memory as passive storage; let only Python own memory updates.
- Decision: memory is now retrieved before planning, injected into execution requests, and updated after execution through transcript-linked runtime memory.
- Consequences: memory is part of the runtime lifecycle instead of dead utility code.

## ADR-009: Specialist Agents Are Execution Roles, Not Competing Brains

- Context: the platform needs multi-agent execution without duplicating cognitive authority.
- Alternatives: parallel independent brains; cosmetic delegation.
- Decision: planner, researcher, and memory agents are specialist execution roles under one master orchestrator.
- Consequences: delegation is observable and scoped, while architectural authority remains singular.

## ADR-010: Phase 2 Audit And Transcript Logging Must Happen In The Live Python->Rust Path

- Context: the active host uses Python as the bridge between the Node brain and the Rust executor.
- Alternatives: rely only on Node-side audit hooks; defer runtime observability until the direct Node bridge is stable.
- Decision: append transcript and execution audit entries from the Python bridge for every externally executed action.
- Consequences: the tested live path now produces runtime evidence even when execution is deferred out of Node.

## ADR-011: Session Isolation Is Required For Deterministic Runtime Validation

- Context: the runtime intentionally preserves per-session context and memory.
- Alternatives: validate all smoke tests against the default session; disable persistence during testing.
- Decision: phase 2 validation uses explicit `AI_SESSION_ID` values to avoid cross-test contamination.
- Consequences: production behavior remains stateful, while engineering validation stays deterministic.

## ADR-012: Packaged Python->Rust Bridge Is The Primary Hardened Runtime Path In Phase 3

- Context: direct Node child-process execution is still host-sensitive, but a packaged Rust bridge is available for Python-mediated execution.
- Alternatives: keep `cargo run` as the implicit default; claim `node-rust-direct` as primary prematurely.
- Decision: prefer `python-rust-packaged`, fall back to `python-rust-cargo`, and keep `node-rust-direct` as explicit opt-in only.
- Consequences: runtime selection is more explicit and less ambiguous without overstating direct-bridge readiness.

## ADR-013: Multi-Step Loop Ownership Lives In The Live Python Orchestrator Path

- Context: the brain plans actions, but the active live path executes externally through Python into Rust.
- Alternatives: keep single-step execution only; attempt a risky mid-phase migration of the entire loop into Node.
- Decision: the authoritative multi-step execution loop is currently owned by the Python orchestrator for the live path, with bounded retries, stop-on-error, and step-level audit.
- Consequences: the active runtime supports real multi-step execution while preserving the brain/executor boundary.

## ADR-014: Specialist System Uses Scoped Registries And Failure Policies

- Context: phase 2 delegation existed but lacked stronger role contracts.
- Alternatives: keep informal delegation; create multiple orchestration authorities.
- Decision: specialist roles now live in a registry with scoped tools, capabilities, and failure policies.
- Consequences: delegation is more observable and more testable without duplicating cognitive authority.

## ADR-015: Runtime Memory Uses Layered Envelopes With Retrieval Hooks

- Context: memory was live but too flat for product-grade growth.
- Alternatives: add a second memory system; overbuild semantic memory immediately.
- Decision: keep one runtime memory store, but split it into session, working, persistent, and semantic-ready envelopes.
- Consequences: retrieval quality improves now, and semantic memory can be added later without re-architecting the store.

## ADR-016: Kairos Requires An Activation Contract Before Runtime Use

- Context: Kairos must be future-activatable without contaminating the core runtime.
- Alternatives: leave Kairos as an undocumented placeholder; integrate it directly into the live runtime.
- Decision: define an explicit contract for activation, scheduling hooks, and context access while keeping Kairos disabled.
- Consequences: the optional feature layer is clearer and safer to evolve later.

## ADR-017: Python Entrypoint Must Seed Runtime Base Paths Explicitly

- Context: path discovery became fragile across different invocation forms and host environments.
- Alternatives: rely only on relative path heuristics; require callers to export `BASE_DIR` manually.
- Decision: `backend/python/main.py` now seeds `BASE_DIR` and `PYTHON_BASE_DIR` automatically when absent.
- Consequences: packaging and operational entrypoint behavior are more deterministic.

## ADR-018: Semantic Memory Uses A Real Lightweight Retrieval Path Before Embedding Backends

- Context: phase 3 prepared semantic-ready storage, but retrieval was not yet affecting live runtime behavior.
- Alternatives: defer semantic retrieval entirely; overbuild a provider-dependent vector stack immediately.
- Decision: implement a real lightweight semantic retrieval layer now using ranked token similarity, recency, and session relevance, while preserving a clean adapter boundary for future embedding-backed upgrades.
- Consequences: semantic retrieval is live and testable without overcommitting to infrastructure that is not operationally ready yet.

## ADR-019: Cognitive Triad Improves Control Without Creating A Second Brain

- Context: stronger runtime quality requires more than raw planning and tool execution.
- Alternatives: let the planner implicitly own quality control; introduce a second orchestration authority.
- Decision: add planner, evaluator, and synthesizer roles under the master orchestrator.
- Consequences: execution quality improves through explicit evaluation and grounded synthesis while architectural authority remains singular.

## ADR-020: Self-Correction Must Be Bounded, Observable, And Conservative

- Context: the runtime needs recovery behavior, but unbounded self-repair would create misleading autonomy and operational risk.
- Alternatives: fail immediately on every recoverable issue; allow open-ended retries and replanning.
- Decision: support bounded retries and targeted action revision with explicit correction reason codes and audit visibility.
- Consequences: the platform gains practical recovery behavior without magical or unsafe repair loops.

## ADR-021: Checkpointing Uses File-Based Run State Before Queue Infrastructure

- Context: resumability is required before a full async job platform exists.
- Alternatives: defer resume entirely; build a distributed queue/worker system immediately.
- Decision: persist normalized checkpoint files with task/run identity and remaining actions, and resume through the orchestrator/task service.
- Consequences: checkpoint/resume is real and testable now, while leaving room for a later durable job backend.

## ADR-022: Product/API Readiness Requires Explicit Task And Run Identity

- Context: future API/server/SaaS exposure needs clearer execution boundaries than session-only runtime state.
- Alternatives: continue using session-only identity; expose raw orchestrator internals externally.
- Decision: introduce explicit task and run identities and a `TaskService` boundary for execute/resume/inspect operations.
- Consequences: the platform is easier to expose safely through future APIs without re-architecting the core runtime.

## ADR-023: Observability Must Correlate Semantic Retrieval, Correction, And Execution Outcomes

- Context: advanced agent debugging requires more than generic success/failure logs.
- Alternatives: keep coarse runtime logging; add opaque debug traces only.
- Decision: enrich audit records with event types, task/run IDs, evaluation outcomes, correction events, and semantic retrieval metadata.
- Consequences: runtime behavior is materially easier to debug, validate, and operate.

## ADR-024: Phase 5 Uses Local Vector Embeddings Before External Providers

- Context: the platform now needs embedding-backed retrieval in a live path, but provider-backed embeddings are not yet operationally required.
- Alternatives: keep lightweight lexical retrieval only; depend immediately on an external embedding provider.
- Decision: implement a real local deterministic embedding adapter and persist vector-aware semantic entries behind a modular boundary.
- Consequences: vector retrieval is live and testable now, and the adapter can later swap to a provider-backed embedding source without re-architecting memory.

## ADR-025: The Critic Is A Conditional Specialist, Not A Second Planner

- Context: runtime quality needs another review layer for risky plans and weak execution outcomes.
- Alternatives: let the evaluator absorb all critique logic; create a second planning authority.
- Decision: add a bounded critic specialist that only approves, revises, retries, or stops under orchestrator control.
- Consequences: quality control improves without creating competing orchestration hierarchy.

## ADR-026: Graph Planning Is Opt-In And Compatibility-Preserving

- Context: richer tasks benefit from dependency-aware execution, but many tasks remain simple.
- Alternatives: force every task into a graph; keep only flat step lists forever.
- Decision: support graph plans only when useful and fall back to linear plans otherwise.
- Consequences: the runtime gains graph execution power without making simple paths more fragile.

## ADR-027: Parallelism Is Limited To Safe Read-Only Work

- Context: the runtime needs higher throughput for some tasks, but careless concurrency would risk corruption and permission confusion.
- Alternatives: keep everything sequential; enable broad unconstrained parallelism.
- Decision: permit bounded parallel execution only for safe read-only graph nodes.
- Consequences: the system becomes faster where safe while preserving execution authority and permission discipline.

## ADR-028: Checkpoint Validation Must Reject Stale Or Incompatible Resume State

- Context: resumability becomes riskier once graph state and richer long-run execution are introduced.
- Alternatives: trust all checkpoint files blindly; disable resume for graph plans.
- Decision: validate checkpoint freshness and plan signatures before resuming.
- Consequences: resume becomes safer and more operationally honest, even if some resumes are blocked instead of guessed through.

## ADR-029: Service-Facing Task Contracts Must Stay Separate From Orchestrator Internals

- Context: the platform is moving closer to future API/server exposure.
- Alternatives: expose raw orchestrator internals externally; defer service boundaries until a full API exists.
- Decision: define normalized start/status task envelopes in `TaskService` and `service_contracts.py`.
- Consequences: future API layers can wrap stable contracts instead of binding directly to internal runtime state.

## ADR: Hierarchical Planning Strategy
- Context: Phase 5 already supported linear and graph planning, but complex tasks needed goal/subgoal grouping.
- Decision: add `plan_hierarchy` as metadata alongside the existing executable step list and graph.
- Consequence: the runtime keeps one execution authority while gaining resumable hierarchy lineage.

## ADR: Execution Learning Memory
- Context: the runtime needed bounded learning without uncontrolled self-training.
- Decision: store explicit execution lessons in a structured file-backed memory and retrieve them before planning.
- Consequence: future plans can be shaped by success and failure-avoidance patterns while staying auditable.

## ADR: Reflection Policy
- Context: post-run quality review was missing from the live path.
- Decision: add bounded reflection summaries triggered by hierarchy or weak execution outcomes.
- Consequence: the system gains review and learning updates without introducing hidden self-talk loops.

## ADR: Tool Governance Taxonomy
- Context: tool safety rules were scattered across permission and runtime logic.
- Decision: classify tools by category, mutability, privilege level, and specialist scope before execution.
- Consequence: policy stops become explicit, auditable, and easier to extend.

## ADR: Operational Policy Model
- Context: operator-facing stop reasons needed to become first-class runtime outputs.
- Decision: attach structured policy decisions to actions and surface them in status, audit, and reflection.
- Consequence: debugging and operator supervision become clearer.

## ADR: Telemetry Summary Schema
- Context: future UI/dashboard work needs correlated run-level summaries.
- Decision: persist machine-readable run summaries with hierarchy, reflection, and step lineage.
- Consequence: dashboard/API work can be added later without redesigning runtime telemetry.

## ADR: Operator Contract Boundaries
- Context: service readiness needed richer inspection paths without exposing a full public API yet.
- Decision: extend internal task service contracts for hierarchy, reflection, learning, and policy inspection.
- Consequence: the project is more operator-ready while preserving clean boundaries.

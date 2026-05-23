# Integration TODO

- [x] Define the main architectural ownership across brain, executor, and provider layers
- [x] Create an explicit brain-to-executor contract
- [x] Rewire the active runner to a fusion brain facade
- [x] Add provider abstraction wrapper inspired by OpenClaude
- [x] Add a JS permission bridge aligned with the Rust runtime policy
- [x] Add session snapshot and transcript audit persistence
- [x] Add Kairos as an isolated optional feature manifest
- [x] Add initial Node test coverage for runner fusion primitives
- [x] Install an extracted QueryEngine-style authority and demote the heuristic fusion facade
- [x] Add a real Rust executor bridge using selected `claw-code-main` runtime exports
- [x] Route live execution requests from Node through Python into the Rust bridge
- [x] Wire runtime memory retrieval and transcript-linked memory updates into the live path
- [x] Add specialist delegation for planner, researcher, and memory roles
- [x] Add end-to-end phase 2 tests for execution, permissions, memory, and audit behavior
- [x] Emit runtime transcript and audit logs from the active Python->Rust execution path
- [x] Add explicit runtime mode selection with primary and fallback execution paths
- [x] Add a bounded multi-step execution loop in the live runtime path
- [x] Harden specialist roles with scopes and failure policies
- [x] Professionalize runtime memory into layered envelopes with retrieval hooks
- [x] Formalize Kairos activation boundaries and contract
- [x] Stabilize Python entrypoint bootstrap with explicit base-path seeding
- [x] Introduce real semantic retrieval that affects runtime context selection
- [x] Add planner/evaluator/synthesizer cognitive control roles in the live system
- [x] Add bounded self-correction and revision logic with audit visibility
- [x] Add checkpoint creation and resumable run execution
- [x] Add task/run identity and task service boundaries for product/API readiness
- [x] Enrich observability with semantic, correction, and step-level execution metadata
- [x] Upgrade semantic retrieval to embedding-backed vector retrieval in one live path
- [x] Add a bounded critic specialist for risky plan/outcome review
- [x] Introduce graph-aware planning with dependency-ready execution state
- [x] Enable one safe parallel read-only execution path
- [x] Harden checkpoint validation with stale-state blocking and graph persistence
- [x] Normalize service-facing task start/status contracts
- [x] Emit vector, critic, graph, and parallel runtime events
- [ ] Package or transpile the selected upstream `src.zip` QueryEngine implementation for deeper direct adoption
- [ ] Replace `cargo run` bridge mode with a stable packaged executor binary for Windows hosts
- [ ] Expand the Rust bridge tool surface beyond file operations
- [ ] Deepen final synthesis quality for richer analysis/planning tasks in the Python live path
- [ ] Remove remaining transitional direct-execution code paths once the packaged bridge is stable
- [ ] Reduce operational dependence on explicit session isolation for ad hoc smoke validation
- [ ] Add provider-backed embeddings behind the current vector adapter
- [ ] Add stronger concurrency controls around checkpoint resume for future multi-worker deployment
- [ ] Extend graph planning beyond read/search dependency shapes
- [ ] Add richer task/run inspection endpoints on top of TaskService
- [ ] Add confidence decay and aging windows to ranked strategy memory
- [ ] Add richer branch merge policies beyond winner-selection
- [ ] Add explicit approval objects before allowing mutating branch exploration
- [ ] Add richer cooperative contribution scoring per specialist role
- [ ] Add operator/dashboard consumers for Phase 7 run intelligence payloads

## Phase 6 follow-up
- [ ] Add mid-run reflection triggers for long-running weak-success paths.
- [ ] Add richer learning-memory ranking and confidence decay.
- [ ] Add operator endpoints on top of the internal service contracts.
- [ ] Add explicit human-approval workflow objects for high-risk tasks.
- [ ] Add hierarchical synthesis formatting for longer analytical answers.
- [ ] Add dashboard/API consumers for `run-summaries.jsonl` and policy events.

## Phase 7 follow-up
- [ ] Expand branch execution beyond read-only analysis once rollback/approval models exist.
- [ ] Add deeper simulation heuristics for dependency and environment blockers.
- [ ] Add per-strategy decay and promotion thresholds.
- [ ] Add richer fusion formatting for analytical responses with multiple branches.

## Phase 8 follow-up
- [ ] Add subtree-specific resume and retry orchestration instead of whole-run continuation.
- [ ] Add richer merge semantics for sibling subtrees beyond winner-selection.
- [ ] Add cost-aware promotion and decay windows in strategy optimization.
- [ ] Add operator/API endpoints over execution state and supervision payloads.
- [ ] Add distributed worker adapters behind the tree execution model.

## Phase 9 follow-up
- [ ] Expand repository intelligence from manifest/structure analysis into deeper import and symbol relationships.
- [ ] Add multi-file patch planning and coordinated rollback across several edited files.
- [ ] Add richer failure diagnosis heuristics beyond simple assertion/operator repair.
- [ ] Add true workspace branch/worktree isolation for longer engineering tasks.
- [ ] Add patch approval workflows for human-in-the-loop engineering review.
- [ ] Persist engineering strategy outcomes back into ranked strategy memory more explicitly.
- [ ] Add stronger code review heuristics for risky dependency and configuration edits.
- [ ] Add operator/dashboard consumers for repository analysis, patch history, and debug iteration payloads.

## Phase 10 follow-up
- [ ] Extend the live large-project path from planning-heavy coordination into governed multi-file patch-set execution.
- [ ] Add milestone-specific resume and retry policies instead of run-level continuation only.
- [ ] Add stronger impact reasoning from symbols, exports, and interface boundaries instead of file/import heuristics only.
- [ ] Add lint and typecheck discovery/execution to the verification planner when repositories expose those tools.
- [ ] Add Git branch/worktree-backed workspace isolation for PR-ready mutation flows.
- [ ] Add human approval checkpoints for high-risk milestone transitions and wide patch sets.
- [ ] Add richer integration specialists for architectural refactors and dependency upgrades.
- [ ] Add dashboard/API consumers for milestone, patch-set, verification, and PR-summary payloads.

# Phase 3 Surgical Report

## What Changed

- The runtime now selects an explicit execution mode through [`runtime/execution/runtimeMode.js`](./runtime/execution/runtimeMode.js).
- The active brain authority in [`core/brain/queryEngineAuthority.js`](./core/brain/queryEngineAuthority.js) now supports bounded multi-step planning and execution requests.
- Specialist delegation is no longer implicit only; roles, scopes, and failure policies now live in [`core/agents/specialistRegistry.js`](./core/agents/specialistRegistry.js).
- Runtime memory was professionalized into layered envelopes in [`storage/memory/runtimeMemoryStore.js`](./storage/memory/runtimeMemoryStore.js).
- Kairos now has an explicit feature contract in [`features/kairos/contract.js`](./features/kairos/contract.js).
- Python-side runtime execution now performs bounded multi-step iteration, step-level logging, and runtime memory synchronization.

## Primary Execution Path

Primary live path in this host:

`User -> Node QueryEngine authority -> Python orchestrator bridge -> packaged Rust executor if available -> cargo-based Rust fallback if needed -> result ingestion -> transcript/audit/memory update -> final response`

In the current workspace, the selected primary execution mode is:

- `python-rust-packaged` when the compiled bridge exists
- fallback to `python-rust-cargo`

## Fallback Execution Path

- `python-rust-cargo` is the explicit fallback mode for hosts where the packaged executor is unavailable or fails.
- `node-rust-direct` exists only as an explicit opt-in path and is **not** the claimed primary mode in this host.

## What Became More Production-Grade

- Runtime mode selection is explicit instead of inferred by scattered bridge logic.
- Multi-step execution is bounded by max steps, timeout, retry policy, and stop-on-error semantics.
- Specialist roles now have clear tool scopes and failure policies.
- Memory now separates session, working, persistent, and semantic-ready hooks in one envelope without reintroducing duplicate authorities.
- Kairos is still isolated, but now has a real activation contract instead of only a placeholder manifest.
- Bootstrap behavior for the Python entrypoint is more deterministic through explicit `BASE_DIR` / `PYTHON_BASE_DIR` defaults.

## What Remains Deferred

- Direct `Node -> Rust` execution is still experimental and not the primary path.
- The Rust bridge still exposes a narrow tool surface focused on file-system actions.
- The authoritative TypeScript brain is an extracted QueryEngine kernel rather than a fully packaged upstream module bundle.
- Semantic retrieval is hook-ready, but not yet backed by embeddings or vector search.

## Risks

1. Windows path encoding and `\\?\` path forms still require careful normalization around Rust file results.
2. `cargo run` fallback is slower than a packaged executor binary and should remain fallback-only.
3. Provider routing is structurally separated, but model-backed cognitive execution still depends on environment configuration.

## Next Recommended Phase

1. Package the Rust executor bridge as the default shipped binary for Windows hosts.
2. Broaden the Rust tool surface beyond read/search/write primitives.
3. Deepen post-execution synthesis for analysis/planning tasks after multi-step tool runs.
4. Introduce semantic memory retrieval behind the current runtime memory interface.

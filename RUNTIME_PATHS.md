# Runtime Paths

## Primary Live Runtime Path

1. `js-runner/queryEngineRunner.js` invokes [`core/brain/fusionBrain.js`](./core/brain/fusionBrain.js)
2. `fusionBrain.js` forwards to [`core/brain/queryEngineAuthority.js`](./core/brain/queryEngineAuthority.js)
3. The brain selects runtime mode using [`runtime/execution/runtimeMode.js`](./runtime/execution/runtimeMode.js)
4. For live execution in this host, the brain emits an `execution_request`
5. [`backend/python/brain/runtime/orchestrator.py`](./backend/python/brain/runtime/orchestrator.py) executes the request step-by-step
6. [`backend/python/brain/runtime/rust_executor_bridge.py`](./backend/python/brain/runtime/rust_executor_bridge.py) calls the Rust bridge
7. [`backend/rust/src/bin/executor_bridge.rs`](./backend/rust/src/bin/executor_bridge.rs) enforces permissions and executes tools
8. Results flow back into Python for transcript, audit, and memory updates
9. The final response is returned to the caller

## Fallback Runtime Path

- Primary mode selection: `python-rust-packaged`
- Fallback mode: `python-rust-cargo`
- Experimental opt-in mode: `node-rust-direct`

`node-rust-direct` is present for future hardening, but it is not the claimed primary path in this workspace.

## Runtime Mode Selection

Selection owner:

- [`runtime/execution/runtimeMode.js`](./runtime/execution/runtimeMode.js)

Inputs:

- `OMINI_EXECUTION_MODE`
- `OMINI_ENABLE_NODE_RUST_DIRECT`
- compiled bridge availability under `backend/rust/target/.../executor_bridge.exe`

Rules:

- If a compiled Rust bridge exists, prefer `python-rust-packaged`
- If it is unavailable or fails, fall back to `python-rust-cargo`
- Use `node-rust-direct` only with explicit opt-in and a stable host

## Permission Enforcement

Permission enforcement lives in:

- [`backend/rust/src/bin/executor_bridge.rs`](./backend/rust/src/bin/executor_bridge.rs)

Current policy:

- `read_file`, `glob_search`, `grep_search` -> allowed
- `write_file` -> prompt/approval required
- destructive shell execution -> denied

## Transcript, Memory, and Audit

Runtime transcript:

- `.logs/fusion-runtime/runtime-transcript.jsonl`

Execution audit:

- `.logs/fusion-runtime/execution-audit.jsonl`

Runtime memory store:

- `.logs/fusion-runtime/runtime-memory-store.json`

Python session transcripts:

- `backend/python/transcripts/*.jsonl`

## Specialist Delegation Interaction

The master brain delegates planning and execution responsibilities before tool execution:

- planner specialist decomposes the task
- memory specialist injects retrieval context
- researcher/coder specialists own step tool scopes
- reviewer specialist normalizes the final result
- Rust remains the only execution authority

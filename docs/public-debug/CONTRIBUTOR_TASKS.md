# Public Debug Contributor Tasks

## High-priority task areas

### 1. Runtime truth validation

Goal:
- verify that reported runtime lanes match what actually happened

Useful starting points:
- `backend/python/brain/runtime/orchestrator.py`
- `backend/python/brain/runtime/observability/`
- `docs/audits/brain-runtime-flow-map.md`

### 2. Cross-runtime contract debugging

Goal:
- find mismatches between Rust, Python, and Node envelopes or execution semantics

Useful starting points:
- `backend/rust/src/main.rs`
- `backend/python/main.py`
- `js-runner/queryEngineRunner.js`
- `docs/architecture/bridge-pipeline.md`
- `docs/architecture/bridge-response-contract.md`

### 3. True action execution reliability

Goal:
- improve success rate once `true_action_execution` is reached

Useful starting points:
- `backend/python/brain/runtime/orchestrator.py`
- `core/brain/queryEngineAuthority.js`
- runtime action execution tests

### 4. Reproduction and diagnostics

Goal:
- add small, repeatable tests or repro steps for degraded behavior

Useful starting points:
- `tests/runtime/`
- `tests/smoke/`
- `docs/public-debug/REPRODUCTION.md`

### 5. Public documentation clarity

Goal:
- make broken or partial behavior easier for contributors to understand

Useful starting points:
- `README.md`
- `CONTRIBUTING.md`
- `docs/public-debug/PROJECT_STATUS.md`

## Good first contributions

- tighten a repro case for one runtime lane
- improve one public debug document with evidence
- add one regression test for a proven runtime-path bug
- improve one GitHub issue template field so reports are easier to act on
- add one regression test for a bridge failure class such as `NODE_BRIDGE_INVALID_JSON` or `PYTHON_BRIDGE_EMPTY_STDOUT`

## Rules for public debug contributions

- keep changes small
- do not hide degraded behavior
- do not remove failing tests to make CI green
- do not commit secrets, logs, local DBs, or private memory stores

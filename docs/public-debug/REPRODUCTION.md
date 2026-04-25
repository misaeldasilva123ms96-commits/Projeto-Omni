# Public Debug Reproduction Guide

## Goal

This repository is open for public debugging, not for pretending the runtime is fully healthy. Contributors should be able to reproduce current behavior, degraded paths, and observability signals without guessing the setup.

## Minimum environment

- Node.js 20+
- Python 3.11+
- Rust toolchain

Optional:

- Bun, if you want parity with some local JS workflows

## Install

```bash
npm install
pip install -r backend/python/requirements.txt
```

Optional training dependencies:

```bash
pip install -r omni-training/requirements.txt
```

## Basic validation sequence

Run Node-side tests:

```bash
npm run test:node
```

Run Python-side tests:

```bash
npm run test:python
```

Run the chat contract:

```bash
npm run test:e2e:chat-contract
```

## Reproducing current runtime behavior

Run the Python entrypoint:

```bash
python backend/python/main.py
```

Run the Rust API:

```bash
cargo run --manifest-path backend/rust/Cargo.toml
```

Representative prompts for inspection:

- greeting: `ola`
- generic conversational: `o que e uma api?`
- memory-style prompt: `qual e o meu nome?`
- runtime explanation: `explique o fluxo do runtime Omni`
- tool-capable prompt: `analise o arquivo package.json`

## What to look for

When reproducing a bug or degraded path, capture:

- prompt used
- command used
- platform and versions
- `runtime_mode`
- `runtime_reason`
- `semantic_runtime_lane`
- `execution_runtime_lane`
- `execution_path_used`
- `fallback_triggered`
- `compatibility_execution_active`
- `provider_actual`
- `execution_provenance`
- whether the result was matcher, local direct response, bridge, true action execution, or fallback

## How to inspect runtime truth

The canonical mode definitions live in:

- [../architecture/runtime-modes.md](../architecture/runtime-modes.md)

The frontend chat status panel now exposes the last turn's runtime debug fields directly. When reproducing a bug through the browser, open the right-side status panel and inspect:

- `Runtime mode`
- `Runtime reason`
- `Execution path`
- `Fallback triggered`
- `Compatibility execution`
- `Provider actual`
- `Provider failed`
- `Failure class`
- whether `Cognitive runtime inspection` is present
- whether `Execution provenance` is present
- `Provider diagnostics`
- `Provider fallback routing`
- `No provider available`

Recommended interpretation order:

1. `runtime_mode`
2. `runtime_reason`
3. `semantic_runtime_lane`
4. `execution_runtime_lane`
5. `execution_path_used`
6. `fallback_triggered`
7. `compatibility_execution_active`
8. `provider_actual` and `execution_provenance`

## Cognitive decision diagnosis

The canonical decision-quality rules live in:

- [../architecture/cognitive-decision-model.md](../architecture/cognitive-decision-model.md)

The curated regression dataset lives in:

- `tests/cognitive/decision_dataset.yaml`

To validate decision quality directly:

```bash
python -m pytest -q tests/cognitive/test_decision_quality.py
```

When reporting a decision bug, include:

- the exact prompt
- expected strategy
- expected tool, if any
- expected `primary_execution_type`
- actual `decision_reasoning`
- actual `decision_reason_codes`
- actual `decision_suggested_tools`

For learning-loop inspection:

- [LEARNING_DEBUGGING.md](./LEARNING_DEBUGGING.md)

## Tool runtime diagnosis

For tool-capable prompts, inspect these fields before reading backend logs:

- `tool_execution.tool_selected`
- `tool_execution.tool_attempted`
- `tool_execution.tool_succeeded`
- `tool_execution.tool_failed`
- `tool_execution.tool_denied`
- `tool_execution.tool_failure_class`
- `tool_execution.tool_failure_reason`
- `tool_execution.tool_latency_ms`

Interpretation:

- `tool_attempted=false`
  - the turn planned or exposed a tool, but did not actually execute one
- `tool_denied=true`
  - governance/policy/operator blocked the action
- `tool_failed=true`
  - the tool runtime was reached and failed after attempt
- `tool_succeeded=true`
  - the action executed successfully

If `tool_failed=true` but:

- `provider_failed=false`
- `failure_class` is empty or bridge-safe

then the problem is downstream in the tool runtime, not in provider routing.

## Bridge failure diagnosis

Use `error.failure_class` first when the response is degraded at a runtime boundary.

Current bridge failure classes:

- `PYTHON_BRIDGE_EMPTY_STDOUT`
- `PYTHON_BRIDGE_INVALID_JSON`
- `PYTHON_BRIDGE_NONZERO_EXIT`
- `NODE_BRIDGE_EMPTY_STDOUT`
- `NODE_BRIDGE_INVALID_JSON`
- `NODE_BRIDGE_NONZERO_EXIT`
- `NODE_BRIDGE_TIMEOUT`
- `NODE_EMPTY_RESPONSE`
- `FRONTEND_RESPONSE_SHAPE_MISMATCH`

Layer hints:

- `PYTHON_*`: Rust did not receive a valid public JSON object from Python
- `NODE_*`: Python did not receive a valid public JSON object from Node
- `FRONTEND_RESPONSE_SHAPE_MISMATCH`: Python main could not normalize the internal response into the public shape

Provider hints:

- `provider_failed=true` with `failure_class` starting with `provider_` indicates a provider-layer failure
- `provider_diagnostics` tells you whether a provider was only configured/selected or actually attempted
- `no_provider_available=true` means Omni had no non-embedded provider available and relied on local behavior

## How to report classification bugs

When reporting a wrong-classification bug, include:

- the exact prompt
- the full `cognitive_runtime_inspection` payload
- whether Node actually executed
- whether `execution_request.actions` existed
- whether the turn was expected to be matcher, local direct, bridge, true action, compatibility, or fallback

## Known current debug posture

- Some prompts still route through compatibility-heavy execution.
- The repository intentionally exposes degraded or partial behavior rather than hiding it.
- A response existing does not prove the strongest runtime path was taken.
- A response existing also does not prove the bridge itself was healthy; check `error.failure_class` and `signals.execution_path_used`.

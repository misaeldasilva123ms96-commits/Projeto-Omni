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

Recommended interpretation order:

1. `runtime_mode`
2. `runtime_reason`
3. `semantic_runtime_lane`
4. `execution_runtime_lane`
5. `execution_path_used`
6. `fallback_triggered`
7. `compatibility_execution_active`
8. `provider_actual` and `execution_provenance`

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

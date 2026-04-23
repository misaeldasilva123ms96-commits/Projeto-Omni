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
- `semantic_runtime_lane`
- `execution_runtime_lane`
- whether the result was matcher, local direct response, bridge, true action execution, or fallback

## Known current debug posture

- Some prompts still route through compatibility-heavy execution.
- The repository intentionally exposes degraded or partial behavior rather than hiding it.
- A response existing does not prove the strongest runtime path was taken.

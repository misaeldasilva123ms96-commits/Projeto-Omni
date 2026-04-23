# Contributing to Omni

## Before you start

Omni is an open source runtime under active debugging. Please do not assume a path is healthy only because it returns a response. A useful contribution is one that improves clarity, reproducibility, observability, or reliability.

## Local setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Rust toolchain

### Install dependencies

```bash
npm install
```

Optional subproject installs:

```bash
pip install -r backend/python/requirements.txt
pip install -r omni-training/requirements.txt
```

## Running locally

Run the Node-side tests:

```bash
npm run test:node
```

Run the Python-side tests:

```bash
npm run test:python
```

Run everything:

```bash
npm test
```

Run the Python entrypoint:

```bash
python backend/python/main.py
```

Run the Rust API:

```bash
cargo run --manifest-path backend/rust/Cargo.toml
```

## Opening a pull request

Please keep PRs small and focused.

Recommended flow:

1. Create a branch for one problem only.
2. Add or update tests when behavior changes.
3. Update documentation when the runtime behavior, contract, or repo structure changes.
4. Explain what evidence you used to justify the change.

## Contribution rules

- Do not commit secrets, credentials, or local `.env` values.
- Do not remove failing tests just to make CI green.
- Do not hide degraded behavior behind vague success messaging.
- Do not rewrite large runtime subsystems without evidence and scoped tests.
- Prefer additive changes over breaking public contracts.
- If a change affects Rust/Python/Node boundaries, mention that explicitly in the PR.

## What areas need help

- Rust/Python/Node runtime boundary debugging
- execution-lane reliability
- observability truthfulness
- test coverage around real runtime paths
- contributor onboarding and developer setup clarity
- documentation cleanup and public-facing explanations

## Good entry points

- [docs/public-debug/PROJECT_STATUS.md](docs/public-debug/PROJECT_STATUS.md)
- [docs/audits/brain-runtime-flow-map.md](docs/audits/brain-runtime-flow-map.md)
- [docs/architecture/runtime-flow.md](docs/architecture/runtime-flow.md)

## Expectations for tests

If you change behavior, run the most relevant tests you can locally and mention what you ran in the PR. If you cannot run a full validation, say what was skipped and why.

# Omini v1.0.0

## What is Omini?

Omini is a hybrid AI agent runtime that combines a Rust bridge, a Python orchestration layer, a Node.js reasoning runner, internal multi-agent coordination, and heuristic self-evolution.

## Included in this release

- Rust subprocess bridge for the Python runtime
- Python brain with memory, sessions, transcripts, swarm orchestration, and evolution loop
- Node runner with formal payload validation and explicit reasoning pipeline
- Internal specialized agents for routing, planning, execution, critique, and memory
- Docker-based deployment foundation and GitHub Actions automation

## Installation

```bash
git clone <your-repo-url>
cd omini
cp .env.example .env
npm install
docker compose up -d --build
```

## Breaking changes

- None in this initial release

## Next steps

- Stronger evaluation heuristics
- Broader automated test coverage
- Better production observability and debug tooling

# Contributing

Thank you for contributing to Omini.

## Development Setup

### Prerequisites

- Python `3.11+`
- Node.js `20+`
- Rust toolchain
- Docker

### Local setup

```bash
git clone <your-repo-url>
cd omini
cp .env.example .env
npm install
```

### Python runtime

```bash
cd backend/python
python main.py "hello"
```

### Rust bridge

```bash
cd backend/rust
cargo run
```

## Commit Standard

Use Conventional Commits:

- `feat: add memory scoring`
- `fix: correct session merge order`
- `refactor: simplify swarm routing`
- `docs: rewrite architecture guide`
- `chore: update CI workflow`

## Adding a New Swarm Agent

1. Create a new file in `backend/python/brain/swarm/`.
2. Inherit from `BaseAgent`.
3. Implement:
   - `receive()`
   - `think()`
   - `act()`
   - `respond()`
4. Register the new agent profile in `backend/python/brain/registry.py`.
5. Route the agent in `swarm_orchestrator.py`.
6. Document the agent behavior in `backend/python/brain/swarm/README.md`.

## Adding a New Capability

1. Add a new capability handler in `backend/python/brain/registry.py`.
2. Register it in the `CAPABILITIES` map.
3. Update `recommend_capabilities()` if routing should discover it automatically.
4. If the capability influences strategy, ensure the evolution layer can observe its usage.

## Running Tests and Checks

### Python compile check

```bash
python -m py_compile backend/python/main.py
```

### Node runner health

```bash
npm run health
```

### Python smoke test

```bash
cd backend/python
python main.py "test"
```

### Docker smoke test

```bash
docker compose up -d --build
docker compose ps
```

## Pull Request Checklist

- [ ] The change is scoped and documented
- [ ] No secrets or real credentials were added
- [ ] No absolute local filesystem paths were introduced
- [ ] Python files compile successfully
- [ ] The relevant runtime path was tested locally
- [ ] Documentation was updated when behavior changed
- [ ] The PR title follows Conventional Commits

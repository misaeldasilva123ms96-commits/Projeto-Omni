# Performance Baseline

## Environment

- host OS: Windows desktop environment
- project root: [project](C:\Users\Misael\OneDrive\Área de Trabalho\Projeto omini\Projeto omini\project)
- branch: `feat/fase1-verify`
- date: 2026-04-07

## Commands executed

### Python direct runtime

```powershell
python backend/python/main.py "leia package.json"
```

### Node runner timing

```powershell
node js-runner/queryEngineRunner.js <runner-payload-json>
```

### Rust HTTP validation

```powershell
cargo run --manifest-path backend/rust/Cargo.toml --bin omini-api
POST http://127.0.0.1:3001/chat
```

### Docker baseline validation

```powershell
docker compose up -d --build
docker compose ps
docker compose logs python-brain
docker compose logs node-runner
```

Observed result:

- `docker compose up -d --build`: OK
- `project-python-brain-1`: `Up (healthy)`
- `project-node-runner-1`: `Up (healthy)`
- both service logs showed no functional errors
- only non-blocking warning observed: obsolete `version` field in `docker-compose.yml`

## Raw measurements

### Python direct runtime latency across 5 requests

- 3458.96 ms
- 3261.93 ms
- 3079.03 ms
- 3318.42 ms
- 3535.86 ms

Average:

- 3330.84 ms

### Python -> Node runner subprocess time across 5 requests

- 291.61 ms
- 288.62 ms
- 257.00 ms
- 231.97 ms
- 239.42 ms

Average:

- 261.73 ms

### Payload size Python -> Node

- 126 bytes for the audited runner payload

### Average `/chat` latency across 5 requests

- 3113.29 ms
- 3334.80 ms
- 3029.13 ms
- 3378.33 ms
- 3117.32 ms

Average:

- 3194.57 ms

### Rust -> Python execution time

Status: approximated from the real `/chat` end-to-end path on the repaired local host

Observed:

- Rust HTTP route startup and request handling are functional
- returned payload shows `source = "python-subprocess"`
- the `/chat` timings above represent the full Rust -> Python -> Node roundtrip

## Unavailable or blocked metrics

### RAM usage of `python-brain` container via `docker stats`

Status: NOT COLLECTED IN THIS PHASE 1 CLOSURE

Reason:

- Docker health was confirmed cleanly, but `docker stats` was not required for this final closure step

## Notes

This baseline now characterizes:

- Python direct runtime
- Node runner subprocess cost
- full Rust `/chat` roundtrip latency
- confirmed healthy Docker service startup for `python-brain` and `node-runner`

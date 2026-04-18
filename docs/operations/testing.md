# Operations: testing

## Python

From the repository root:

```bash
python -m unittest discover -s tests/runtime -p "test_*.py"
```

Focused areas:

- `tests/runtime/evolution/` — controlled evolution
- `tests/runtime/improvement/` — Phase 40 orchestrator
- `tests/runtime/observability/` — read models
- `tests/runtime/reasoning/` — reasoning + orchestrator integration

## Node / CI

See `.github/workflows/` for the authoritative CI matrix and scripts invoked in pipelines.

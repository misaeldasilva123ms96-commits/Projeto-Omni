# OMNI SQLite Memory Facade

## Architecture

```
Omni Runtime
  ↓
Memory Facade / Storage Facade  (brain.memory.memory_facade)
  ↓
SQLite Adapter                   (brain.memory.sqlite_adapter)
  ↓
JSONL Audit Mirror               (brain.memory.jsonl_audit_mirror)
```

The **Memory Facade** is a safe abstraction layer for structured memory persistence
in OMNI. It mediates between two backends:

- **JSONL** (default): Append-only audit mirror. No dependencies. Always available.
- **SQLite** (opt-in): Structured relational storage. Requires explicit enable.

Both backends can operate simultaneously. The JSONL mirror always receives writes
even when SQLite is enabled, providing an audit trail.

## Memory Types

| Table               | Purpose                                     |
|---------------------|---------------------------------------------|
| conversations       | Structured conversation records              |
| messages            | Individual messages within conversations     |
| episodes            | Structured episodic memory                   |
| semantic_facts      | Learned semantic knowledge                   |
| runtime_events      | Execution event tracking                     |
| provider_attempts   | Provider API call metadata (no secrets)      |
| governance_events   | Policy/governance resolution records         |
| learning_artifacts   | Training/learning artifact references        |

## Configuration

Safe defaults:

| Variable                    | Default                    | Description                       |
|----------------------------|----------------------------|-----------------------------------|
| `OMINI_MEMORY_BACKEND`     | `jsonl`                    | Active backend (`jsonl`/`sqlite`) |
| `OMINI_ENABLE_SQLITE_MEMORY` | `false`                  | Enable SQLite adapter             |
| `OMINI_SQLITE_MEMORY_PATH` | `.omni/memory/omni-memory.sqlite` | SQLite database path      |
| `OMINI_JSONL_MEMORY_PATH`  | `.omni/memory/omni-audit.jsonl`  | JSONL audit mirror path    |

### Examples

```python
# JSONL only (default, safest)
facade = MemoryFacade()
facade.initialize()

# SQLite + JSONL
facade = MemoryFacade(enable_sqlite=True)
facade.initialize()

# Via env vars
os.environ["OMINI_ENABLE_SQLITE_MEMORY"] = "true"
facade = MemoryFacade()
facade.initialize()
```

## Safety & Redaction

- **No secrets stored**: `api_key`, `token`, `secret`, `password`, `credential`,
  `auth_token`, and `authorization` keys are redacted (`[REDACTED]`) before any write.
- **No raw prompts stored**: Runtime events store evidence references, not full payloads.
- **Message content truncated**: Messages are truncated to 500 characters.
- **Provider metadata filtered**: Sensitive metadata keys are stripped before write.
- **Error sanitization**: File paths are sanitized in error messages.
- **SQLite optional**: If SQLite init fails, the facade falls back to JSONL-only.

## Error Handling

| Scenario                          | Behavior                               |
|-----------------------------------|----------------------------------------|
| SQLite disabled, backend=jsonl    | JSONL mirror used                      |
| SQLite disabled, backend=sqlite   | Init error set, no writes              |
| SQLite enabled, init succeeds     | Both SQLite + JSONL                    |
| SQLite enabled, init fails        | JSONL only, init_error set             |
| SQLite write fails at runtime     | Error caught silently, JSONL continues |

## Rollout Plan

1. **Phase 1** (this branch): Facade contracts, SQLite adapter, JSONL mirror, tests.
2. **Phase 2**: Wire facade into runtime paths behind feature flags.
3. **Phase 3**: Enable SQLite by default after soak testing.
4. **Phase 4**: Deprecate JSONL fallback for structured memory.

## Migration

Existing JSONL/JSON memory files are preserved. This facade does not replace
current runtime memory behavior. The existing `brain.runtime.memory.MemoryFacade`
continues to operate independently.

## Testing

```bash
cd backend/python
python -m pytest tests/memory/test_memory_facade.py -v
python -m pytest tests/memory/test_sqlite_adapter.py -v
python -m pytest tests/memory/test_jsonl_audit_mirror.py -v
```

## Files

| File                                  | Role                                 |
|---------------------------------------|--------------------------------------|
| `brain/memory/__init__.py`            | Module exports                       |
| `brain/memory/memory_models.py`       | Data contracts and redaction         |
| `brain/memory/memory_facade.py`       | Safe Memory Facade                   |
| `brain/memory/sqlite_adapter.py`      | SQLite adapter                       |
| `brain/memory/jsonl_audit_mirror.py`  | JSONL audit mirror                   |
| `brain/memory/schema.sql`             | SQL schema (documentation)           |
| `tests/memory/test_memory_facade.py`  | Facade tests                         |
| `tests/memory/test_sqlite_adapter.py` | SQLite adapter tests                 |
| `tests/memory/test_jsonl_audit_mirror.py` | JSONL mirror tests              |
| `docs/memory/sqlite-memory-facade.md` | This document                        |

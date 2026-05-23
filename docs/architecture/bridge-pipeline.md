# Bridge Pipeline

This document maps the real Omni execution pipeline:

Rust → Python → Node/Bun → Python → Rust → Frontend

## Pipeline map

1. Rust HTTP entry
   - file: `backend/rust/src/main.rs`
   - endpoints:
     - `POST /chat`
     - `POST /api/v1/chat`
   - responsibility:
     - receive public request
     - normalize client session metadata
     - call Python over subprocess stdin/stdout

2. Rust → Python bridge
   - file: `backend/rust/src/main.rs`
   - function:
     - `call_python(...)`
   - contract:
     - stdin carries a single JSON object
     - stdout must return a single JSON object
     - stderr is captured separately and never treated as success payload

3. Python entrypoint
   - file: `backend/python/main.py`
   - responsibility:
     - load bridge message from stdin
     - call `BrainOrchestrator.run(...)`
     - sanitize internal runtime output into public JSON
     - reserve stdout for the final JSON object

4. Python orchestration
   - file: `backend/python/brain/runtime/orchestrator.py`
   - responsibility:
     - choose execution path
     - call Node runner when needed
     - execute returned actions
     - build runtime inspection

5. Python → Node bridge
   - files:
     - `backend/python/brain/runtime/js_runtime_adapter.py`
     - `backend/python/brain/runtime/node_transport.py`
   - responsibility:
     - select Bun/Node executable
     - pass payload via stdin
     - capture stdout/stderr separately
     - reject empty stdout and malformed JSON

6. Node runner
   - file: `js-runner/queryEngineRunner.js`
   - responsibility:
     - load execution authority
     - run QueryEngine / adapter
     - preserve structured payloads
     - return one JSON object to stdout

7. Node execution authority
   - files:
     - `core/brain/queryEngineAuthority.js`
     - `core/brain/executionProvenance.js`
   - responsibility:
     - choose matcher / local / bridge / action path
     - emit execution provenance
     - return structured `execution_request` when action execution is needed

8. Python return path
   - file: `backend/python/brain/runtime/orchestrator.py`
   - responsibility:
     - interpret Node payload
     - execute actions when present
     - build `cognitive_runtime_inspection`

9. Rust return path
   - file: `backend/rust/src/main.rs`
   - responsibility:
     - parse Python stdout strictly
     - preserve `cognitive_runtime_inspection`, `providers`, and `error`
     - reject silent empty success

10. Frontend client
   - files:
     - `frontend/src/lib/api/chat.ts`
     - `frontend/src/lib/api/adapters.ts`
     - `frontend/src/types.ts`
   - responsibility:
     - consume flattened response envelope
     - tolerate additive fields such as `error` and `cognitive_runtime_inspection`

## Failure points

### Rust → Python

- Python subprocess spawn failure
- Python non-zero exit
- Python empty stdout
- Python invalid JSON

### Python → Node

- Node runner not found
- Node timeout
- Node non-zero exit
- Node invalid JSON
- Node empty stdout

### Node semantic layer

- empty `response`
- missing `execution_request` when one is expected
- bridge-only payload without action execution

### Public response shaping

- empty response field
- missing response and missing error
- malformed JSON at any boundary

## Stability rule

No boundary may treat these as success:

- empty stdout
- invalid JSON
- `{ "response": "" }`
- missing response and missing error
- null response

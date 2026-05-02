# PHASE 11B - NODE INTERNAL QUERYENGINE SERVICE

Date: 2026-05-01

Base branch: architecture/python-service-11a

Base commit: 5e93a8e5795437c3083b160f37b354de539b219e

Working branch: architecture/node-service-11b

## Scope

Phase 11B adds a Node internal HTTP service entrypoint for QueryEngine execution while preserving the existing CLI/subprocess runner. Python and Rust are not switched to Node service mode in this phase.

## Files Changed

- `js-runner/queryEngineService.js`
- `tests/runtime/nodeQueryEngineService.test.mjs`
- `docs/architecture/node-internal-query-engine-service.md`
- `docs/audit/PHASE_11B_NODE_SERVICE.md`
- `package.json`

## Service Entrypoint

- `js-runner/queryEngineService.js`
- npm script: `npm run start:node-service`

## Endpoints

- `POST /internal/query-engine/run`
- `GET /internal/query-engine/health`
- `GET /internal/query-engine/readiness`

## CLI/Subprocess Compatibility

The existing `js-runner/queryEngineRunner.js` CLI/subprocess behavior remains intact. Phase 11B does not switch Python or Rust to service mode.

## Security Posture

- default host: `127.0.0.1`
- no CORS
- internal-only documentation warning
- taxonomy-shaped public errors
- public-safe recursive response sanitizer
- no raw env, secrets, stack traces, stdout/stderr, command args, raw provider/tool/memory payloads in service responses

## Env Vars

- `OMNI_NODE_SERVICE_HOST`
- `OMNI_NODE_SERVICE_PORT`
- `OMINI_NODE_SERVICE_HOST`
- `OMINI_NODE_SERVICE_PORT`

## Tests / Validation Results

Commands executed:

- `node --check js-runner/queryEngineService.js`
  - Result: PASS
- `node tests/runtime/nodeQueryEngineService.test.mjs`
  - Result: PASS
- `npm run test:security`
  - Result: PASS, exit code 0
- `npm test`
  - Result: TIMEOUT after 180 seconds
  - Follow-up: `npm run test:python` also timed out after 180 seconds
  - Classification: aggregate/unittest timeout, not specific to the Node service implementation
- `npm run test:js-runtime`
  - Result: PASS, exit code 0
- `npm run test:python:pytest`
  - Result: PASS, exit code 0
- `npm --prefix frontend run typecheck`
  - Result: PASS, exit code 0
- `cd backend/rust && cargo test`
  - Result: PASS, 38 passed
- `python -m py_compile backend/python/main.py backend/python/brain_service.py`
  - Result: PASS
- `git diff --check`
  - Result: PASS with CRLF warning for `package.json`

Narrow Phase 11B validation passed. Broad `npm test` timeout was isolated to the aggregate Python unittest command.

## Known Limitations

- Python still calls the Node CLI/subprocess runner. Service client integration is not part of Phase 11B.
- Rust does not call the Node service.
- Circuit breaker behavior belongs to Phase 11C/11D.

## Rollback

Revert the Phase 11B commit on `architecture/node-service-11b`.

## Gate 11B Status

Status: PASSED.

Gate evidence:

- Node internal service entrypoint exists.
- `/internal/query-engine/run`, `/internal/query-engine/health`, and `/internal/query-engine/readiness` exist.
- Node CLI/subprocess mode is preserved and covered by test.
- Responses are public-safe and recursively sanitized.
- Runtime truth, governance/tool status, and taxonomy-shaped errors are preserved where present.
- Service defaults to loopback host.
- Tests were added and executed.
- No merge into main.

## No Merge Into Main

This phase does not merge into main.

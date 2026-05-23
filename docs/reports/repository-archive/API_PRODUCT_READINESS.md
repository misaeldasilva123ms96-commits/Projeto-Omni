# API Product Readiness

## User / Session / Task / Run Boundaries

- `user_id`: external caller identity, currently surfaced through `TaskService`
- `session_id`: conversation or continuity boundary
- `task_id`: logical task identity inside a session
- `run_id`: concrete execution attempt identity

## External Invocation Model

Current minimal service surface:

- [`backend/python/brain/runtime/task_service.py`](./backend/python/brain/runtime/task_service.py)

Supported operations:

- `execute_task`
- `resume_task`
- `inspect_run`

## Config / Environment Boundaries

Important runtime configuration:

- `OMINI_EXECUTION_MODE`
- `OMINI_MAX_STEPS`
- `OMINI_MAX_RETRIES`
- `OMINI_STEP_TIMEOUT_MS`
- `OMINI_MAX_CORRECTION_DEPTH`
- `BASE_DIR`
- `PYTHON_BASE_DIR`

## Deployment Bootstrap Readiness

- Python entrypoint now seeds base paths automatically when absent
- runtime mode selection is explicit
- packaged vs cargo fallback is documented and observable

## What Is Needed Next For API / Server / SaaS Exposure

1. expose `TaskService` behind an HTTP or RPC layer
2. authenticate and authorize `user_id`
3. isolate persistent memory by user/session namespace more formally
4. add external transcript/audit inspection endpoints
5. move checkpoint storage to a service-grade backing store if needed

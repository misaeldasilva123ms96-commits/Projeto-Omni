# Omni Access Layer Plan Policy Foundation

This document describes the Phase 1 PlanPolicy foundation for Omni Access Layer.
It is a contract layer only: it defines plan modes, public policy shape, default
limits, and validation rules without changing Omni brain behavior.

## Location

- Contract: `backend/python/brain/runtime/access_layer/plan_policy.py`
- Tests: `tests/runtime/test_plan_policy.py`

## Plan Modes

The foundation supports these modes:

- `free`
- `byok`
- `pro`
- `internal`

Each policy exposes:

- `daily_token_limit`
- `max_input_tokens`
- `max_output_tokens`
- `max_context_tokens`
- `files_enabled`
- `tools_enabled`
- `sensitive_tools_enabled`
- `long_memory_enabled`
- `provider_mode`

Unknown plan modes are rejected explicitly. Public policy serialization only
includes contract fields and does not expose provider keys or secrets.

## Future Phases

This phase intentionally does not integrate Puter.js, BYOK key storage, Pro
billing, provider routing, or any runtime behavior changes. Those remain future
phases layered on top of this contract.

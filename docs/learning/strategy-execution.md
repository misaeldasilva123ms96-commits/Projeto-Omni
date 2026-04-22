# Strategy Execution

## Purpose

Phase 4 turns the selected runtime strategy into an explicit execution path instead of leaving execution behavior spread across implicit branches in the orchestrator.

## How it works

The control plane now builds a `StrategyExecutionRequest` from:

- the selected strategy
- the execution manifest
- the OIL summary
- the routing decision
- the ranked decision
- relevant tool metadata

The `StrategyDispatcher` chooses a concrete executor for:

- `DIRECT_RESPONSE`
- `TOOL_ASSISTED`
- `MULTI_STEP_REASONING`
- `NODE_RUNTIME_DELEGATION`
- `SAFE_FALLBACK`

Each executor can either:

- run the compatibility execution path already used by the runtime
- downgrade safely
- block execution when guardrails require it

## Safety

The dispatcher never overrides governance. If execution becomes unsafe or inconsistent, the runtime falls back to the compatibility path or to `SAFE_FALLBACK`.

## Current limits

The executors currently encapsulate the existing runtime path instead of replacing it with fully separate backends. This keeps Phase 4 reversible and low-risk.


# Runtime Flow

## High-level flow

User Input → Rust API → Python Brain Runtime → Node/Bun Execution Layer → Python Action Execution / Response Synthesis → Rust Response

## 1. Decision step

The first decision happens in Python.

The Rust API forwards the request to `backend/python/main.py`, which creates the orchestrator runtime. From there, `BrainOrchestrator.run(...)` decides how the turn should proceed.

That decision may involve:

- interpreting the request
- building memory/context
- selecting a strategy
- delegating to Node for execution-side reasoning

## 2. Execution step

The Node/Bun layer can return different kinds of outcomes:

- a matcher shortcut
- a local direct response
- a bridge execution request
- an action-backed execution request

When actions are present, Python can execute them through the runtime action path and then synthesize the final response.

## 3. Fallback step

Omni contains several fallback and degraded paths. These are important because a response existing is not the same thing as a healthy runtime completion.

Fallback behavior can happen because of:

- transport problems
- missing runtime dependencies
- invalid execution payloads
- blocked or degraded execution paths

The project is actively trying to make those paths explicit instead of hiding them.

## 4. Observability

Observability is part of the runtime flow, not an afterthought.

After a turn, Omni can attach runtime inspection data that describes:

- the semantic lane
- the execution lane
- whether compatibility execution was active
- whether the result was degraded or partial

This is one of the main ways contributors can tell the difference between:

- real execution
- bridge-only behavior
- shortcut behavior
- degraded fallback

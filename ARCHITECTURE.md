# Architecture

## Overview

Omini is structured as a layered runtime rather than a single process with mixed responsibilities. Each layer has a narrow contract:

```text
Client
  |
  v
Rust API
  |
  v
Python Brain
  |
  v
Swarm Orchestrator
  |
  v
Node Runner
  |
  v
Persistent State
```

This design keeps the Rust-facing contract simple while letting Python and Node handle orchestration and reasoning.

## Architectural Decisions

### 1. Rust handles the external HTTP boundary

Why:

- strong typing and predictable request/response handling
- process isolation from the cognitive runtime
- clear subprocess boundary for Python

Tradeoff:

- one more layer to operate
- subprocess orchestration must remain stable

### 2. Python owns orchestration and persistence

Why:

- it is the best fit for memory, sessions, transcripts, scoring, and strategy control
- orchestration logic is easier to audit and evolve in Python

Tradeoff:

- subprocess calls to Node require strict contracts

### 3. Node owns the explicit reasoning pipeline

Why:

- the adapter pipeline is easier to express and iterate in JavaScript
- delegate resolution and runner schema validation fit naturally in the Node layer

Tradeoff:

- interop requires schema stability

### 4. Swarm is internal, not vendor-managed

Why:

- no dependence on hosted swarm APIs
- complete control over traces, messages, and agent lifecycle
- deterministic local execution on CPU-only infrastructure

### 5. Strategy evolution is parameter-based

Why:

- no fine-tuning, no GPU assumptions
- changes remain auditable and reversible
- production safety is higher than direct code mutation

## Full Flow

```text
HTTP request
  |
  v
Rust POST /chat
  |
  v
python main.py
  |
  v
BrainOrchestrator
  |
  +--> memory lookup
  +--> transcript merge
  +--> strategy state read
  |
  v
SwarmOrchestrator
  |
  +--> RouterAgent
  +--> PlannerAgent
  +--> ExecutorAgent(s)
  +--> CriticAgent
  +--> MemoryAgent
  |
  v
Node runner + reasoning adapter
  |
  v
final text response
  |
  +--> evaluation
  +--> learning update
  +--> session snapshot
  +--> transcript append
  +--> swarm log append
```

## Interface Contracts

### Rust -> Python

Contract:

- input: CLI argument with user message
- output: stdout only, final response text only

Guarantee:

- Rust never needs to understand internal swarm or evolution structures

### Python -> Node

Contract file:

- [`contract/runner-schema.v1.json`](./contract/runner-schema.v1.json)

Payload shape:

```json
{
  "message": "string",
  "memory": {
    "nome": "string",
    "preferencias": ["string"]
  },
  "history": [
    {
      "role": "user | assistant",
      "content": "string"
    }
  ],
  "summary": "string",
  "capabilities": [
    {
      "name": "string",
      "description": "string",
      "category": "string"
    }
  ],
  "session": {
    "session_id": "string",
    "summary": "string"
  }
}
```

Validation:

- performed in `js-runner/queryEngineRunner.js` using `ajv`

## Hybrid Memory Strategy

Omini uses two complementary memory forms:

### Structured memory

Files:

- `backend/python/memory.json`
- `backend/python/memory/user.json`
- `backend/python/memory/preferences.json`

Used for:

- user identity
- explicit preferences
- short structured state

### Operational memory

Files:

- `backend/python/transcripts/*.jsonl`
- `backend/python/brain/runtime/sessions/*.json`
- `backend/python/brain/runtime/swarm_log.json`
- `backend/python/memory/learning.json`

Used for:

- recent dialogue recall
- agent trace reconstruction
- evaluation history
- strategy evolution

## Swarm Task Distribution

Internal agent order:

```text
RouterAgent
  -> PlannerAgent
  -> ExecutorAgent(s)
  -> CriticAgent
  -> MemoryAgent
```

Communication model:

- in-memory `asyncio.Queue`
- typed messages
- session-scoped payloads
- persisted communication trace in `swarm_log.json`

Message shape:

```json
{
  "from": "agent_id",
  "to": "agent_id | broadcast",
  "type": "task | result | critique | memory_op",
  "payload": {},
  "timestamp": "ISO8601",
  "session_id": "string"
}
```

## Self-Evolution Loop

The evolution loop never rewrites orchestrator code. It only updates strategy files that the orchestrator reads.

```text
Response
  |
  v
Evaluator
  |
  v
Pattern Analyzer
  |
  v
Strategy Updater
  |
  +--> strategy_state.json
  +--> snapshots/strategy_vN.json
  +--> strategy_log.json
  |
  v
Future requests read the new parameters
```

Current adjustable parameters:

- capability weights
- decision thresholds
- memory history limits
- orchestrator hints

Rollback:

```text
python -m brain.evolution.dashboard rollback <version>
```

## Auditability

Omini keeps every major adaptive artifact inspectable:

- session snapshots
- transcripts
- swarm communication logs
- evaluations
- strategy snapshots
- strategy logs

That makes it possible to trace why a response happened and what parameter version shaped it.

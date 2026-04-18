# Kairos Contract

## Role

Kairos is an optional advanced feature layer for:

- scheduled follow-ups
- recurring tasks
- assistant continuity
- notification-ready workflows

Kairos is **not**:

- the main brain
- the execution authority
- a parallel orchestration system

## Activation Conditions

Kairos should only be activated when:

- the core brain/executor path is stable
- runtime mode selection is explicit
- transcript and memory lifecycles are already reliable
- scheduling hooks are intentionally configured

## Scheduling Hooks

Current contract supports these future hooks:

- `follow-up`
- `scheduled-check`
- `recurring-task`

## Memory / Context Access Rules

Kairos may:

- read session memory
- read persistent memory
- read recent transcript context

Kairos may not:

- mutate execution authority
- bypass permission policy
- become the final answer authority without handing work back to the master runtime

## Interaction With Main Runtime

1. Kairos receives a scheduled or proactive trigger
2. Kairos prepares a bounded task envelope
3. The task is handed back to the master orchestrator
4. The normal brain -> executor path runs
5. Results are persisted through the same transcript/memory/audit lifecycle

## Current Code Ownership

- Manifest: [`features/kairos/manifest.js`](./features/kairos/manifest.js)
- Contract: [`features/kairos/contract.js`](./features/kairos/contract.js)

## Deferred Areas

- scheduler implementation
- notification transport
- recurring task persistence
- proactive execution policy UI/API controls

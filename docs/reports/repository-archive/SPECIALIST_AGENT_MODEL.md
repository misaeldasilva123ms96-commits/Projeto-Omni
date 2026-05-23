# Specialist Agent Model

## Authority Model

- One master authority: `master_orchestrator`
- Specialist agents are delegated roles, not competing brains
- Rust is still the only execution authority

## Specialist Roles

### `task_planner`
- Responsibility: task decomposition, constraints, step ordering
- Allowed tools: none directly
- Failure policy: `fallback-to-master`

### `memory_manager`
- Responsibility: inject session/working/persistent context and memory hints
- Allowed tools: none directly
- Failure policy: `degrade-context`

### `researcher_agent`
- Responsibility: read/search-oriented workspace actions
- Allowed tools:
  - `read_file`
  - `glob_search`
  - `grep_search`
- Failure policy: `stop-on-read-failure`

### `coder_agent`
- Responsibility: write-oriented actions after approval
- Allowed tools:
  - `write_file`
- Failure policy: `require-approval`

### `reviewer_agent`
- Responsibility: normalize outputs, surface partial failure, preserve grounded final answers
- Allowed tools: none directly
- Failure policy: `warn-only`

### `provider_router`
- Responsibility: keep provider/model routing outside cognition
- Allowed tools: none directly
- Failure policy: `fallback-to-local`

### `rust_executor`
- Responsibility: execute approved actions and return audited results
- Allowed tools:
  - `read_file`
  - `glob_search`
  - `grep_search`
  - `write_file`
- Failure policy: `authoritative-stop`

## Delegation Contract

Delegation is materialized through:

- [`core/agents/specialistRegistry.js`](./core/agents/specialistRegistry.js)
- [`features/multiagent/delegationLayer.js`](./features/multiagent/delegationLayer.js)

Each delegated specialist entry includes:

- `specialist_id`
- `role`
- `allowed_tools`
- `capabilities`
- `failure_policy`
- `status`

## Result Flow

1. master builds intent and runtime mode
2. planner specialist creates ordered steps
3. memory specialist injects retrieval context
4. researcher/coder specialists own the action identity on each step
5. Rust executes the step
6. reviewer specialist synthesizes the final grounded answer

## Failure Handling

- permission failure stops the loop
- repeated execution failure stops the loop after retry budget
- reviewer never overrides execution truth; it only normalizes reporting

# Orchestrator Structural Audit

Date: 2026-04-22
Phase: C — Orchestrator Structural Audit
Target: `backend/python/brain/runtime/orchestrator.py`

## Executive conclusion

`BrainOrchestrator` is the structural control center of the Python runtime, but it is currently overloaded far beyond safe orchestration responsibilities.

The most important structural finding is this:

- a true strategy-driven execution plane is present conceptually
- but, in the current code, the observed execution paths still collapse into the compatibility runtime path via `compat_execute`
- therefore the orchestrator is simultaneously:
  - coordinator
  - policy gate
  - memory updater
  - runtime path selector
  - Node bridge controller
  - action executor
  - observability emitter
  - provenance carrier
  - session writer
  - evaluation/learning router

This makes the happy path difficult to trust, difficult to test, and easy to misclassify.

## Does a true cognitive execution path exist in code?

### Short answer

Partially, but not as a clean, independent execution path.

### Evidence

The code contains explicit layers for:

- reasoning
- strategy adaptation
- planning
- decision ranking
- strategy dispatch
- multiple strategy executors
- manifest-driven execution

However, the actual dispatch step in `run()` passes all real execution through the compatibility callback:

- `orchestrator.py:1058-1066`

The critical line is:

- `compat_execute=lambda: self._execute_strategy_compatible_path(...)`

This means the strategy executors do not currently own distinct execution backends.

## Exact point where execution collapses into compatibility mode

### Primary collapse point

In `BrainOrchestrator.run`:

- `orchestrator.py:1058-1066`

This is where `_dispatch_strategy_execution(...)` is called and every strategy receives:

- `compat_execute=lambda: self._execute_strategy_compatible_path(...)`

### Secondary collapse point

Inside `StrategyDispatcher.dispatch(...)`:

- `backend/python/brain/runtime/execution/strategy_dispatcher.py`

The dispatcher calls the selected executor, but each concrete executor observed in this audit still uses `compat_execute()` for real work.

### Evidence in executors

- `direct_response_executor.py`
  - if no direct precomputed answer exists, it calls `compat_execute()`
- `multi_step_reasoning_executor.py`
  - bounded-depth gate, then calls `compat_execute()`
- `tool_assisted_executor.py`
  - risk gate, then calls `compat_execute()`
- `node_runtime_delegation_executor.py`
  - availability gate, then calls `compat_execute()`

So the strategy layer is real as a control wrapper, but not yet real as distinct execution ownership.

## Explicit mapping of execution branches inside `BrainOrchestrator.run`

## Branch 1 — Empty message

Location:
- `orchestrator.py:518-520`

Behavior:
- sets fallback mode
- returns safe fallback inspection immediately

Classification:
- valid

## Branch 2 — Mock mode

Location:
- `orchestrator.py` shortly after `run_started_monotonic`

Behavior:
- records mock runtime mode
- returns mock response

Classification:
- valid for testing
- not part of true cognitive execution

## Branch 3 — Reasoning/memory build failure

Location:
- `run()` try/except around:
  - `normalize_input_to_oil_request`
  - `unified_memory.build_reasoning_context`
  - `strategy_engine.select`
  - `reasoning_engine.reason`

Behavior:
- synthesizes fallback reasoning payload
- keeps runtime moving

Classification:
- ambiguous

Reason:
- useful for robustness
- but it allows cognitive stages to fail while preserving forward motion into later layers

## Branch 4 — Reasoning validation block

Location:
- `orchestrator.py:704-709`

Behavior:
- if `reasoning_handoff.proceed` is false
- sets fallback mode
- returns safe fallback immediately

Classification:
- valid

## Branch 5 — Control layer block

Location:
- after `_evaluate_control_layer(...)`

Behavior:
- records control decisions
- may transition mode
- returns blocked response with fallback runtime classification

Classification:
- valid

## Branch 6 — Allowed path into planning + coordination + strategy dispatch

Location:
- central mainline of `run()`

Behavior:
- builds planning payload
- decomposes tasks
- updates structured memory
- computes direct memory answer
- coordinates agents
- dispatches strategy execution

Classification:
- overloaded

Reason:
- too many distinct concerns are still inline in one method

## Branch 7 — Strategy execution path

Location:
- `orchestrator.py:1058-1066`
- `_dispatch_strategy_execution(...)`

Behavior:
- selected strategy is wrapped into `StrategyExecutionRequest`
- but real execution is still delegated to `compat_execute`

Classification:
- misleading

Reason:
- structurally it looks like a real strategy control plane
- operationally it still routes through the same compatibility lane

## Branch 8 — Compatibility runtime path

Location:
- `_execute_strategy_compatible_path(...)`
- `orchestrator.py:3068-3231`

Behavior:
- if `direct_response` exists, returns early with local payload
- otherwise:
  - computes policy hint
  - runs performance optimizer
  - invokes `self.swarm_orchestrator.run(...)`
  - passes `_async_node_execution(...)`
  - merges node envelope metadata/provenance/hints into swarm result

Classification:
- overloaded
- dangerous

Reason:
- this function is the actual shared execution backend for most strategies
- it hides multiple semantic modes inside one “compatibility” label

## Branch 9 — Node subprocess path

Location:
- `_call_node_query_engine(...)`
- `orchestrator.py:2144-2496`

Behavior:
- preflight checks
- subprocess spawn
- timeout / exception / bad stdout -> Node fallback
- valid JSON -> may return:
  - direct response with no execution request
  - response without actions
  - execution request that triggers `_execute_runtime_actions(...)`

Classification:
- valid as boundary
- ambiguous as semantic source of truth

Reason:
- this function handles both real execution requests and shortcut/local response paths, then normalizes them into `last_runtime_mode = live`

## Branch 10 — Real action execution path

Location:
- `_call_node_query_engine(...)` when `execution_request.actions` exists
- then `_execute_runtime_actions(...)`

Behavior:
- registers run
- planning executor ensures plan
- control layer re-evaluates action execution
- executes actions / branches / batches
- synthesizes runtime response from step results

Classification:
- potentially true cognitive path
- but not isolated enough at the top-level run path

Reason:
- this is the closest thing to a real non-shortcut execution path
- but it is buried behind Node bridge behavior and not clearly separated from local shortcut responses

## Are executors real execution layers or thin wrappers?

### Finding

They are currently thin wrappers over the compatibility runtime path.

### Evidence

Direct code evidence:

- `direct_response_executor.py`
  - either returns precomputed direct response
  - or uses `compat_execute()`

- `multi_step_reasoning_executor.py`
  - checks max step depth
  - then uses `compat_execute()`

- `tool_assisted_executor.py`
  - checks risk metadata
  - then uses `compat_execute()`

- `node_runtime_delegation_executor.py`
  - checks node availability
  - then uses `compat_execute()`

### Structural interpretation

The executor layer is real as:
- policy/guardrail wrapper
- trace emitter
- status labeler

It is not yet real as:
- separate execution ownership
- distinct backend selection
- isolated happy path

## Where routing is chosen inside `run()`

Routing/decision points inside the method:

1. `strategy_engine.select(...)`
   - strategy adaptation signal

2. `reasoning_engine.reason(...)`
   - reasoning handoff and proceed/block decision

3. `_evaluate_control_layer(...)`
   - routing decision + policy/evidence gating

4. `_build_runtime_upgrade_artifacts(...)`
   - OIL summary + manifest generation

5. `_apply_decision_ranking(...)`
   - may change effective selected strategy

6. `_dispatch_strategy_execution(...)`
   - wraps selected strategy into current execution control plane

The problem is not absence of decision points.
The problem is that those decision points do not yet fan out into genuinely separate execution lanes.

## Where fallback is implicitly applied

### Explicit fallbacks

- empty message
- mock mode
- reasoning validation block
- control layer block
- node subprocess failures

### Implicit/structural fallbacks

1. reasoning-stage exceptions are wrapped and execution continues
2. strategy executors fall through to `compat_execute()`
3. Node shortcut/local/bridge responses are treated as live execution success
4. Python public sanitizer can collapse operational payloads into safe user fallback

These implicit fallbacks are the main structural risk because they preserve output without preserving semantic truth.

## Where control is handed to Node

Control is handed to Node in two nested places:

1. `_execute_strategy_compatible_path(...)`
   - calls `self.swarm_orchestrator.run(...)`
   - passes `_async_node_execution(...)`

2. `_async_node_execution(...)`
   - calls `_call_node_query_engine(...)`

3. `_call_node_query_engine(...)`
   - invokes the Node subprocess
   - then decides whether the returned Node payload is:
     - direct response
     - response without actions
     - execution request with actions

## Where `cognitive_runtime_inspection` is built and where Node truth may be lost

### Build point

`cognitive_runtime_inspection` is produced in:

- `_emit_cognitive_runtime_inspection(...)`
- which calls `build_cognitive_runtime_inspection(...)`

### Node truth preservation attempt

Node truth is captured in `_call_node_query_engine(...)`:

- `_last_node_result_envelope`
- `_last_node_cognitive_hint`

When a parsed Node payload contains `cognitive_runtime_hint`, it is stored:

- `orchestrator.py:2374-2379`

### Where truth appears to be lost or flattened

Even though `_last_node_cognitive_hint` is captured, the final runtime classification still often ends up as:

- `runtime_mode = NODE_EXECUTION_SUCCESS`
- `last_runtime_reason = direct_node_response`

instead of:

- `MATCHER_SHORTCUT`
- `NO_TOOL_LOCAL`
- bridge-only partial path

Code-based reason:

- `_call_node_query_engine(...)` assigns:
  - `last_runtime_mode = "live"`
  - `last_runtime_reason = "direct_node_response"`
  whenever parsed Node output has a string response and no `execution_request`

This assignment happens before final truth classification and collapses several distinct Node semantic paths into one coarse live-success bucket.

## Responsibility classification

## Valid

- path detection and project root resolution
- trusted execution policy construction
- cognitive runtime inspection emission
- context budget helpers
- some run registry / session / memory synchronization helpers
- explicit Rust/Node subprocess fallback handling

## Overloaded

- `BrainOrchestrator.__init__`
  - too many subsystem instantiations and ownership boundaries

- `BrainOrchestrator.run`
  - currently mixes:
    - session bootstrap
    - memory loading
    - reasoning
    - control/gating
    - manifest/ranking
    - planning
    - memory writes
    - coordination
    - strategy dispatch
    - learning
    - evaluation
    - evolution
    - transcript/session persistence
    - final inspection

- `_execute_strategy_compatible_path`
  - de facto unified execution backend for multiple strategies

- `_execute_runtime_actions`
  - huge execution engine embedded inside orchestrator

## Ambiguous

- reasoning exception fallback inside `run`
- `_call_node_query_engine`
  - mixes subprocess reliability concerns with semantic path interpretation

- final relation between:
  - `strategy_execution_status`
  - `last_runtime_reason`
  - `runtime_mode`
  - true user-visible completion

## Misleading

- strategy dispatch layer as currently wired
  - looks like strategy-specific execution
  - still routes most real work through compatibility execution

- `NODE_EXECUTION_SUCCESS` as currently derived
  - too broad to represent healthy completion

- manifest-driven execution flag
  - can be true while actual execution still took the legacy compatibility lane

## Dangerous

- inline coupling between orchestrator decision logic and actual Node subprocess semantics
- hidden semantic collapse at `_call_node_query_engine(...)`
- single-method control concentration in `run()`
- coexistence of:
  - true action execution path
  - shortcut/local response path
  - bridge-preparation response path
  under the same top-level success framing

## Risk-ranked function list

### Highest risk

- `BrainOrchestrator.run`
- `_execute_strategy_compatible_path`
- `_call_node_query_engine`
- `_execute_runtime_actions`

### Medium-high risk

- `_dispatch_strategy_execution`
- `_apply_decision_ranking`
- `_build_runtime_upgrade_artifacts`
- `_emit_cognitive_runtime_inspection`

### Lower risk / extraction-safe

- budget helpers
- policy/evidence serialization helpers
- transcript/history compaction helpers
- JSONL append/sanitize helpers

## Extraction plan proposal

This is a plan proposal only. No remediation is applied in this phase.

## Extraction Step 1 — Separate semantic path classification from transport success

Create an explicit module responsible for classifying the Node result into:

- matcher shortcut
- local direct response
- bridge-only execution request
- true executed action result
- degraded fallback

Why first:
- this is the minimum change needed later to stop flattening Node truth into generic live success

## Extraction Step 2 — Split `run()` into orchestration stages with explicit contracts

Recommended stage boundaries:

- input/session bootstrap
- reasoning + memory context
- control/governance gating
- manifest/ranking preparation
- execution dispatch
- post-execution learning/evaluation
- persistence + inspection emission

Why:
- `run()` is currently too overloaded to reason about the happy path

## Extraction Step 3 — Promote a true execution lane separate from compatibility execution

Keep the compatibility path intact, but make it explicit as:

- `compatibility_execution_path`

Then allow future strategy executors to own distinct paths:

- `direct_local_path`
- `node_shortcut_path`
- `bridge_execution_request_path`
- `true_action_execution_path`

Why:
- this is the only safe way to preserve existing behavior while enabling a genuine cognitive path

## Extraction Step 4 — Move `_call_node_query_engine` semantic interpretation out of subprocess boundary code

Keep subprocess mechanics in one boundary module.
Move interpretation of parsed Node payload into a separate classifier.

Why:
- transport success and semantic success are currently conflated

## Extraction Step 5 — Reduce misleading executor semantics

Keep executor wrappers, but later make them own real backends or explicit path selection instead of always delegating to `compat_execute()`.

Why:
- current executor layer is structurally promising but semantically thinner than it appears

## Minimal viable path to a true cognitive path without breaking behavior

Future-safe proposal:

1. Preserve current compatibility runtime exactly as one explicit lane
2. Add explicit result-type classification for Node outputs
3. Change final inspection/input to consume classified path types, not just coarse `last_runtime_reason`
4. Promote only one real action-backed path as the “true cognitive path”
5. Leave matcher/local/bridge paths alive, but label them truthfully

That would allow:

- true cognitive execution to exist as a separate audited path
- compatibility fallback to remain stable
- conversational shortcut to remain fast without pretending to be full execution

## Bottom line

The orchestrator is not structurally broken because it lacks cognitive concepts.
It is structurally dangerous because too many concepts terminate in the same compatibility lane, and the final runtime truth is flatter than the real internal branching.

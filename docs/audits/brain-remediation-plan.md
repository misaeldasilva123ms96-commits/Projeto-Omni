# Brain Remediation Plan

Date: 2026-04-22
Phase: G — Surgical Remediation Plan
Status: planning only; no code changes applied

## Executive summary

The highest-leverage recovery path is not a rewrite of `BrainOrchestrator`.

The minimum viable recovery plan is:

1. separate transport success from semantic execution classification
2. preserve Node lane truth end-to-end
3. make compatibility execution explicit instead of implicit
4. expose true action-backed execution as a first-class runtime lane
5. only after that, extract deeper orchestrator responsibilities

This ordering preserves backward compatibility while making runtime truthfulness auditable.

## Confirmed structural defects from phases A-C

### D1. Strategy dispatch does not currently own real execution backends

Evidence:

- `backend/python/brain/runtime/orchestrator.py:1058-1066`
- `_dispatch_strategy_execution(...)` receives:
  - `compat_execute=lambda: self._execute_strategy_compatible_path(...)`

Impact:

- all observed strategy lanes collapse into the compatibility path
- executor success does not prove distinct execution ownership

### D2. `_call_node_query_engine(...)` mixes transport and semantic interpretation

Evidence:

- `backend/python/brain/runtime/orchestrator.py:2402-2439`
- parsed payloads without `execution_request` are normalized as:
  - `last_runtime_mode = "live"`
  - `last_runtime_reason = "direct_node_response"`

Impact:

- matcher shortcuts
- local direct responses
- bridge-only responses

are flattened into generic success semantics.

### D3. Node lane truth is captured but not elevated to first-class runtime classification

Evidence:

- `_last_node_cognitive_hint` is populated from Node payloads
- final inspection still often reports broad success classes such as `NODE_EXECUTION_SUCCESS`

Impact:

- Python observability loses the distinction between:
  - matcher shortcut
  - local direct response
  - bridge execution request
  - true action execution

### D4. A real action execution path exists, but is buried

Evidence:

- `execution_request.actions` in Node payload
- `_execute_runtime_actions(...)` exists in Python

Impact:

- true action-backed execution is present in code
- but it is not modeled as an explicit top-level runtime lane

## Target execution lane model

The runtime should classify exactly one primary lane per request.

### Lane 1 — `matcher_shortcut`

Definition:

- Node conversational matcher produced the user-visible response

Expected properties:

- low latency
- no action execution
- not a true cognitive completion

### Lane 2 — `local_direct_response`

Definition:

- Node or Python produced a direct answer without action execution
- response is not a conversational matcher

Expected properties:

- useful for simple requests
- still distinct from full cognitive execution

### Lane 3 — `compatibility_execution`

Definition:

- request was routed through the legacy compatibility path
- used for backward compatibility while remediation is in progress

Expected properties:

- explicit degraded-but-supported lane
- no longer confused with true cognitive execution

### Lane 4 — `bridge_execution_request`

Definition:

- Node produced an execution request / bridge payload
- the system reached the bridge layer, but action-backed completion is not yet established

Expected properties:

- operationally meaningful
- not yet the same as a completed cognitive response

### Lane 5 — `true_action_execution`

Definition:

- Node produced `execution_request.actions`
- Python executed those actions
- the final response was synthesized from the action-backed path

Expected properties:

- first-class cognitive lane
- strongest evidence of real execution

## Ranked remediation plan

### R1. Introduce a semantic runtime lane classifier

Defect summary:

- runtime semantic truth is flattened into generic success

Affected files:

- `backend/python/brain/runtime/orchestrator.py`
- `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`
- new module under `backend/python/brain/runtime/observability/` or `backend/python/brain/runtime/execution/`

Impact:

- high

Risk:

- low to medium if done as additive classification only

Recommended fix type:

- extraction

Validation required:

- unit tests for classification cases
- regression tests for existing inspection fields

Why first:

- this is the smallest change that restores runtime truthfulness without changing execution behavior

### R2. Split Node transport parsing from semantic interpretation

Defect summary:

- `_call_node_query_engine(...)` conflates subprocess/JSON handling with semantic path meaning

Affected files:

- `backend/python/brain/runtime/orchestrator.py`
- new helper module for Node result parsing/classification

Impact:

- high

Risk:

- medium

Recommended fix type:

- extraction

Validation required:

- unit tests for parsed Node payload variants
- transport regression tests

Why second:

- after a classifier exists, transport can hand over normalized Node results instead of hardcoding semantic success

### R3. Preserve Node truth into cognitive runtime inspection

Defect summary:

- Node hint fields exist but final inspection remains too coarse

Affected files:

- `backend/python/brain/runtime/observability/cognitive_runtime_inspector.py`
- `backend/python/brain/runtime/orchestrator.py`

Impact:

- high

Risk:

- low

Recommended fix type:

- normalization and propagation hardening

Validation required:

- inspection tests
- prompt-based regression checks

Why third:

- once semantic lane classification exists, inspection can become trustworthy without changing the public response contract

### R4. Make compatibility execution an explicit lane

Defect summary:

- compatibility execution is currently implicit and visually indistinguishable from healthy completion

Affected files:

- `backend/python/brain/runtime/orchestrator.py`
- `backend/python/brain/runtime/execution/strategy_dispatcher.py`
- related observability modules

Impact:

- high

Risk:

- medium

Recommended fix type:

- extraction and explicit naming

Validation required:

- strategy integration tests
- observability regression tests

Why fourth:

- this reduces masking without forcing a deep executor rewrite yet

### R5. Promote `true_action_execution` to a first-class runtime lane

Defect summary:

- real action execution exists but is structurally buried behind bridge payload handling

Affected files:

- `backend/python/brain/runtime/orchestrator.py`
- `backend/python/brain/runtime/execution/*`
- possibly action/result synthesis helpers

Impact:

- very high

Risk:

- medium to high

Recommended fix type:

- extraction-first restructuring

Validation required:

- runtime action path tests
- end-to-end prompt evidence

Why fifth:

- once truth classification and compatibility labeling are stable, this becomes the first real functional recovery step

### R6. Separate conversational shortcut handling from compatibility execution

Defect summary:

- matcher/local direct responses currently look too similar to general runtime success

Affected files:

- Node authority path
- Python Node result interpretation path

Impact:

- medium to high

Risk:

- medium

Recommended fix type:

- contract clarification

Validation required:

- Node/Python bridge tests
- classification tests

### R7. Extract orchestrator execution staging

Defect summary:

- `run()` remains overloaded and obscures the happy path

Affected files:

- `backend/python/brain/runtime/orchestrator.py`
- new extracted service modules

Impact:

- high

Risk:

- high if attempted too early

Recommended fix type:

- staged extraction

Validation required:

- broad regression suite

Why later:

- extraction is safer after semantic truth and explicit lanes are already stabilized

## Minimal safe starting point

The first remediation block should be:

### Block 1 — Runtime lane normalization without changing execution behavior

Goal:

- stop treating all successful Node-originated responses as the same semantic class

Smallest change with highest impact:

1. introduce a normalized Node outcome structure
2. classify the outcome into one of:
   - `matcher_shortcut`
   - `local_direct_response`
   - `bridge_execution_request`
   - `true_action_execution`
   - `compatibility_execution`
   - `safe_degraded_fallback`
3. preserve current user-visible response behavior
4. update runtime inspection to expose the classified lane
5. keep existing coarse fields for backward compatibility during transition

Why this is the right first block:

- it fixes observability truth before execution semantics
- it does not remove the compatibility path
- it does not break public response shape
- it creates the evidence surface needed for later executor remediation

## Proposed extraction shape

### 1. Transport result layer

Suggested responsibility:

- subprocess invocation
- stdout/stderr capture
- timeout/error normalization
- JSON parsing

Suggested outcome:

- transport success/failure only

### 2. Semantic Node outcome classifier

Suggested responsibility:

- inspect parsed payload
- infer runtime lane
- preserve:
  - `cognitive_runtime_hint`
  - `execution_mode`
  - presence of `execution_request`
  - whether `actions` exist

Suggested outcome:

- explicit semantic lane object independent from transport status

### 3. Runtime inspection mapper

Suggested responsibility:

- translate semantic lane into:
  - `runtime_mode`
  - `cognitive_chain`
  - `final_verdict`
  - fine-grained provenance fields

Compatibility rule:

- preserve existing public fields while adding clearer internal truth

## Backward compatibility requirements

The first implementation block must preserve:

- current public response envelope
- current Rust/Python parse contract
- existing fallback responses
- strategy dispatcher surface
- existing smoke/observability tests where semantics have not been intentionally tightened

Acceptable compatibility evolution:

- additional inspection fields
- more truthful `runtime_mode` classification
- more explicit degraded/shortcut provenance

Not acceptable in the first block:

- removing compatibility execution
- rewriting the orchestrator happy path
- changing the Node bridge contract broadly
- changing user-visible response text generation rules

## Validation expectations for the first remediation block

Minimum required:

- unit tests for lane classification
- regression tests for `cognitive_runtime_inspection`
- representative prompt checks for:
  - greeting
  - local memory-style direct response
  - tool-capable intent
  - bridge execution request
  - degraded fallback

Success criteria:

- no more flattening of matcher/local/bridge into generic `NODE_EXECUTION_SUCCESS`
- true action-backed execution remains distinguishable when it occurs
- compatibility path remains functional

## Recommended implementation order after Phase G

1. Implement Block 1: runtime lane normalization
2. Validate prompt truth table again
3. If successful, extract Node transport parser from semantic classifier
4. Make compatibility execution explicit in inspection and provenance
5. Promote true action execution as a first-class runtime lane
6. Only then begin orchestrator execution extraction

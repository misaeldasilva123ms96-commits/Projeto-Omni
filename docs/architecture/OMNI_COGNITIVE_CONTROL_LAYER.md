# Omni Cognitive Control Layer

## 1. Purpose

Projeto Omni has progressed from a runtime that can execute reasoning to a runtime that must govern reasoning. Through Phase 4, the platform already provides one cognitive authority, one execution authority, hardened bridge behavior, tested engineering workflows, operator-facing telemetry, and a professional interface. What is still missing is an explicit executive layer that decides how reasoning may proceed before the runtime spends capability, mutates state, or declares success.

The Cognitive Control Layer is the architectural boundary that formalizes this governance. Its role is to classify intent, assign execution mode, apply policy, route work to the right capability surface, require evidence before mutation, and connect failures to explicit recovery behavior. It is the foundation for safe autonomy across Phases 11-20.

## 2. Architectural Overview

The high-level flow for the next evolution cycle is:

`intent -> classification -> mode -> policy -> capability routing -> execution -> verification`

At a control level, this means:

1. Intent arrives through the existing Rust -> Python -> Node pipeline.
2. The cognitive authority classifies the task type, scope, risk, and expected outputs.
3. The Mode Engine selects the active runtime mode.
4. The Policy Engine determines whether the requested path is allowed, constrained, or blocked.
5. The Capability Router selects the specialist, tool family, or engineering subsystem best suited to the task.
6. The existing execution authority performs the bounded work.
7. Verification and run intelligence determine whether the result is sufficient, degraded, recoverable, or blocked.

This layer does not add a second brain. It constrains and structures how the existing brain and execution authority operate.

## 3. Mode Engine

The Mode Engine introduces explicit runtime modes. A run may transition between modes, but each transition must be observable, policy-aware, and bounded.

### EXPLORE

Purpose: gather context, inspect repository/runtime state, and identify uncertainty.

Allowed actions:

- read-only repository analysis
- telemetry inspection
- state retrieval
- dependency and impact analysis
- memory retrieval

Disallowed actions:

- code mutation
- git mutation
- success declaration

### PLAN

Purpose: convert gathered context into executable structure.

Allowed actions:

- hierarchical planning
- milestone decomposition
- execution tree generation
- verification planning
- patch-set proposal construction

Disallowed actions:

- uncontrolled execution
- mutation without a verification path

### EXECUTE

Purpose: perform bounded actions already permitted by policy and planning.

Allowed actions:

- tool execution under governance
- patch application under mutation policy
- bounded debug loop activity
- checkpointed milestone advancement

Disallowed actions:

- widening scope without reclassification
- bypassing policy or verification requirements

### VERIFY

Purpose: validate outcomes against plan, policy, and evidence requirements.

Allowed actions:

- targeted tests
- full tests when required
- lint/typecheck when discovered
- patch-set validation
- post-change inspection

Disallowed actions:

- merge-ready declaration without evidence
- policy override through verification shortcuts

### RECOVER

Purpose: respond to recoverable failures through explicit bounded mechanisms.

Allowed actions:

- retry under retry policy
- rollback
- fallback mode selection
- narrower replanning
- degraded response generation

Disallowed actions:

- open-ended self-repair
- hidden mutation during recovery

### REPORT

Purpose: produce grounded operator-facing and reviewer-facing outputs.

Allowed actions:

- run summary generation
- PR-style summary generation
- milestone status reporting
- policy and verification summary emission

Disallowed actions:

- claiming success without verified evidence
- suppressing unresolved blockers

## 4. Policy Engine

The Policy Engine evaluates the active mode, task risk, workspace scope, and requested actions before execution. Policies are structured into the following categories.

### ExecutionPolicy

Controls whether a task may execute immediately, requires planning first, or must stop pending additional evidence or approval.

### MutationPolicy

Controls whether files, patch sets, memory state, or runtime artifacts may be changed, and under what rollback and verification conditions.

### GitPolicy

Controls branch discipline, commit discipline, merge expectations, and mutation boundaries relative to repository state.

### ToolPolicy

Controls which tool family may be used, at what privilege level, and under what context and ordering constraints.

### ScopePolicy

Controls whether the active task remains within declared scope, file set, milestone boundary, and architectural ownership.

### VerificationPolicy

Controls what evidence is required before execution is considered successful, recoverable, merge-ready, or blocked.

## 5. Capability Router

The Capability Router determines how work is dispatched without creating competing authorities.

Routing decisions are based on:

- task class
- mode
- repository context
- evidence availability
- policy constraints
- mutation risk

The router may dispatch to:

- core planning specialists
- repository intelligence modules
- engineering tools
- verification planner
- code review specialist
- large-task planning modules
- existing Python orchestration services

Routing is capability-based, not persona-based. Specialists remain delegated roles. The orchestrator remains the final authority over whether routed work is executed, retried, or blocked.

## 6. Evidence Gate

The Evidence Gate formalizes evidence-first execution. Mutation-capable work should not proceed because a task is merely plausible; it should proceed because the runtime has accumulated enough grounded evidence to justify the change.

Evidence may include:

- repository analysis
- impact map
- dependency observations
- verification plan
- patch-set preview
- policy allow decision
- rollback path
- prior run intelligence

Before mutation, the control layer should be able to answer:

- what will change
- why those files are affected
- how the change will be verified
- how the runtime will recover if verification fails

If those questions cannot be answered with sufficient evidence, the execution path should remain in `EXPLORE` or `PLAN`, or move to `RECOVER`/blocked status instead of mutating optimistically.

## 7. Failure Taxonomy Integration

Future execution should classify failures structurally rather than treating them as generic errors. The control layer integrates with a failure taxonomy such as:

- `classification_failure`
- `policy_block`
- `evidence_insufficient`
- `routing_mismatch`
- `tool_failure`
- `verification_failure`
- `workspace_corruption`
- `timeout_or_budget_exceeded`
- `partial_success`
- `operator_required`

This taxonomy connects directly to recovery behavior:

- retry when bounded retry policy applies
- degrade when a valid lower-capability response exists
- rollback when mutation succeeded but verification failed
- stop when policy or evidence requirements are not met
- escalate when operator approval is required

## 8. Integration with Existing Omni Architecture

The Cognitive Control Layer must extend, not replace, the current platform.

### Connection to Phase 10 modules

The control layer governs and consumes existing large-project primitives:

- `milestone_manager.py` for milestone boundaries and progress
- `patch_set_manager.py` for grouped mutation artifacts
- `pr_summary_generator.py` for grounded report outputs
- `task_service.py` and `service_contracts.py` for inspection-ready contracts
- repository intelligence and verification planning for evidence gathering

### Connection to Phase 3 hardening

The control layer assumes and reuses the hardened live path:

- Rust subprocess timeouts and structured failures
- Python fallback mode
- specialist degradation behavior
- persistence I/O safeguards
- meaningful `/health`

These hardening measures become prerequisites for safe mode transitions and recovery handling.

### Connection to Phase 4 observability

The control layer should emit structured observability that can be surfaced through the current dashboard and read-only endpoints. Phase 4 made the runtime visible; the control layer makes higher-level governance decisions visible.

## 9. Observability Hooks

The following observability hooks should exist when the control layer is implemented:

- mode transition events
- policy evaluation decisions
- capability routing decisions
- evidence gate pass/fail outcomes
- blocked execution reasons
- verification outcomes
- recovery activation events
- operator-escalation signals

These hooks should integrate into existing run intelligence, execution state, runtime signals, and dashboard consumers rather than creating a second observability system.

## 10. Acceptance Criteria

Phase 11 should only be considered implemented when all of the following are true:

- the runtime has an explicit mode model
- mode transitions are observable
- policy evaluation is structured and attached to execution
- capability routing is explicit and inspectable
- mutation-capable execution requires evidence and a verification path
- blocked execution is surfaced as a first-class outcome
- recovery paths are selected from structured failure categories
- the layer integrates with existing task service, execution state, and dashboard surfaces
- no second cognitive authority is introduced

## 11. Expected Impact

This layer creates the architectural bridge for the next roadmap:

- Phase 11 - Cognitive Control Layer: implement the mode and policy scaffolding described here
- Phase 12 - Capability Routing: formalize and operationalize explicit capability dispatch
- Phase 13 - Structured Memory & Context Budget: make memory/context selection mode- and policy-aware
- Phase 14 - Verification-First Engineering: require evidence and validation before success
- Phase 15 - Self-Repair Foundation: connect structured failures to bounded recovery paths
- Phase 16 - Long-Horizon Execution: manage milestone-aware mode transitions across long runs
- Phase 17 - Multi-Agent Review Loop: govern review/debate under explicit routing and policy
- Phase 18 - Operational Intelligence: expand run intelligence into governance analytics
- Phase 19 - Autonomous PR Lifecycle: ground PR mutation, review, and readiness in policy and evidence
- Phase 20 - Self-Evolving Engineering Platform: evolve safely with governed autonomy instead of opaque behavior

The expected impact is not “more autonomy by default.” The expected impact is safer, more explainable, mode-aware autonomy that remains bounded, inspectable, and aligned with operator intent.

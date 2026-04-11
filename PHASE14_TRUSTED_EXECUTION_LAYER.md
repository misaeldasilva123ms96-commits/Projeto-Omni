# Phase 14 - Trusted Execution Layer

## Objective

Phase 14 adds a trusted execution spine to Projeto Omni so meaningful runtime actions are classified, validated, verified, and recorded before they are allowed to influence the system. The goal is to improve execution safety without replacing the current Rust -> Python -> Node architecture or breaking existing runtime contracts.

## Architecture

The trusted execution layer lives under `backend/python/brain/runtime/execution/` and is composed of small, explicit modules:

- `models.py`
  - Typed dataclasses for execution intent, policy, risk, preflight, verification, guardrails, receipts, and trusted results.
- `risk_classifier.py`
  - Deterministic rules that assign `low`, `medium`, `high`, or `critical` risk.
- `preflight_checks.py`
  - Structured safety checks before execution begins.
- `post_action_verifier.py`
  - Deterministic verification of observable outcomes after execution.
- `execution_receipt.py`
  - Receipt construction for audit, memory, and future replay or rollback workflows.
- `execution_guardrails.py`
  - Policy and guardrail decisions that decide whether an action may proceed.
- `trusted_executor.py`
  - The orchestration wrapper that coordinates classification, preflight, execution, verification, and receipt generation.

## Execution Lifecycle

Every trusted action now follows this lifecycle:

1. Build an `ExecutionIntent`
2. Classify deterministic risk
3. Run preflight checks
4. Evaluate guardrails and policy
5. Execute through the existing runtime callback if allowed
6. Verify the outcome deterministically
7. Emit an execution receipt
8. Return the wrapped result back into the existing orchestrator flow

## Risk Model

The current risk model is intentionally explicit and deterministic:

- `low`
  - read-only operations
  - reasoning-style actions
  - verification reads
- `medium`
  - state and memory mutations
- `high`
  - code edits
  - patch application
  - verification and autonomous repair style actions
- `critical`
  - shell execution
  - externally impactful actions
  - package mutation or deployment-like behavior

By default, high-risk actions are allowed to preserve current runtime behavior, while critical actions are blocked unless explicitly enabled by policy.

## Preflight Model

Preflight currently validates:

- capability or tool identifier exists
- capability or tool is registered
- target subsystem is available
- required arguments are present
- current runtime mode allows execution
- current execution policy allows the computed risk
- mutation-prone actions have session context when required
- dry-run awareness is recorded for future extension

Preflight returns structured checks and a clear failure reason instead of a boolean only.

## Verification Model

Post-action verification checks:

- result shape is structured
- successful actions produce non-empty payloads
- expected structural fields exist when declared
- mutation-prone actions expose observable effects
- failures surface coherent error information

Verification is deterministic by design. It is meant to be dependable, inspectable, and easy to extend for later phases.

## Receipt Model

Every trusted execution emits an `ExecutionReceipt` with:

- receipt id
- timestamp
- action id
- action type
- risk level
- preflight status
- execution status
- verification status
- retry count
- rollback status
- summary
- error details
- session, task, and run correlation ids
- structured metadata

Receipts are serializable and are also appended into the existing runtime audit log stream through `runtime.trusted_execution.receipt`.

## Integration Points

The main integration point is `backend/python/brain/runtime/orchestrator.py`, specifically the per-action execution path. Instead of replacing the orchestrator, Phase 14 wraps each meaningful action inside the trusted executor and then hands the result back to the existing retry, evaluation, critic, checkpoint, and logging flow.

This approach keeps the current architecture intact:

- Rust remains the API gateway
- Python remains the main cognitive runtime
- Node and engineering runtimes remain the execution backends
- trusted execution becomes the safety layer around action dispatch

The layer is also aware of the capability registry and existing engineering tools so future phases can build on stable execution semantics.

## Limitations

This phase deliberately does not implement:

- automatic rollback orchestration
- autonomous self-editing
- self-evolution loops
- speculative adaptive safety logic
- external approval workflows

Rollback is represented in receipts, but currently remains `not_applicable` until a concrete rollback engine is introduced.

## How This Enables Phases 15-20

Phase 14 creates the execution backbone required for later autonomy:

- Phase 15 can use receipts to safely drive self-repair
- later phases can compare intended outcome vs observed outcome
- future policy engines can route by trust level instead of only intent
- reversible mutations can later gain real rollback controllers
- history and memory systems can learn from verified receipts instead of raw execution noise

In short, Phase 14 makes Omni's execution path structured enough to support serious future autonomy without normalizing unsafe behavior today.

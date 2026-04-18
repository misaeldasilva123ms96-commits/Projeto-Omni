# Phase 15 - Controlled Self-Repair Layer

## Mission

Phase 15 extends the trusted execution substrate from Phase 14 with a bounded, policy-governed self-repair path. The goal is not unrestricted self-modification. The goal is to detect deterministic failures, decide whether they are safely repairable, validate a small repair, and only then promote it under strict controls.

## Safety Philosophy

The controlled self-repair layer follows seven core principles:

1. bounded mutation only
2. repair only after evidence
3. validation required before promotion
4. smallest effective fix
5. explicit promotion gate
6. full traceability
7. safe failure over risky repair

By default, self-repair is disabled and promotion is disabled. This keeps current runtime behavior stable until an operator explicitly enables the feature.

## Architecture

The layer lives in `backend/python/brain/runtime/self_repair/` and is composed of:

- `models.py`
  - typed dataclasses and enums for evidence, eligibility, hypothesis, scope, proposal, validation, receipt, outcome, and policy
- `failure_analyzer.py`
  - converts trusted execution failures into structured failure evidence and cause hypotheses
- `repair_policy.py`
  - deterministic eligibility and conservative environment-driven defaults
- `repair_scope.py`
  - bounded scope enforcement for allowed roots, files, and mutation limits
- `repair_proposer.py`
  - deterministic repair template catalog
- `repair_validator.py`
  - patch review, source compile, import validation, receipt-smoke checks, targeted test execution, and rollback on failure
- `repair_receipt.py`
  - structured receipt builder
- `repair_executor.py`
  - coordinates eligibility, hypothesis, proposal, scope, validation, and promotion
- `self_repair_loop.py`
  - orchestrator-facing wrapper for failure inspection and replay decisions

## Repair Lifecycle

Every bounded repair follows this sequence:

1. failure evidence is built from trusted execution artifacts
2. eligibility is evaluated by deterministic policy
3. root-cause hypothesis is generated
4. bounded proposal is generated from an allowlisted template catalog
5. repair scope is enforced
6. validation runs
7. repair is promoted or rejected
8. repair receipt is emitted
9. orchestrator decides whether to replay the failed action once or preserve the failure

## Evidence Model

`FailureEvidence` records:

- evidence id
- action id and action type
- subsystem
- failure type and summary
- error details
- verification details
- retry count
- recurrence count
- session, task, and run ids
- source execution receipt ids
- capability and selected agent
- result snapshot

This keeps the self-repair path grounded in Phase 14 receipts and structured runtime output.

## Eligibility Model

Deterministic eligibility returns one of:

- `not_repairable`
- `repairable_within_scope`
- `requires_human_or_future_phase`
- `blocked_by_policy`

Initial repairable failures:

- `verification_failed`
- `missing_result_payload`
- `missing_error_payload`
- `invalid_result_shape`

Initial non-repairable failures:

- external outages
- package manager failures
- deployment failures
- critical-risk blocks
- failures outside the deterministic catalog

## Bounded Scope Model

Phase 15 allows only:

- mutation type: `single_file_runtime_patch`
- maximum files: `1`
- maximum repair attempts per action: `1`
- maximum recurrence before policy block: `2`
- allowed root: `backend/python/brain/runtime`
- allowed targets:
  - `engineering_tools.py`
  - `rust_executor_bridge.py`
  - `execution/*.py`

It explicitly disallows:

- orchestrator rewrites
- frontend, Rust, docs, or config mutation
- lockfiles and generated files
- broad cross-runtime changes

## Validation Model

Validation is mandatory and conservative:

- patch risk review
- source compile validation
- import/load validation
- receipt-level smoke check
- targeted unit test execution where mapped

If promotion is enabled and patch application succeeds, any later validation failure triggers immediate rollback.

## Receipt Model

Each repair attempt generates a `RepairReceipt` with:

- repair receipt id
- timestamp
- evidence id
- proposal id
- eligibility decision
- cause category
- repair strategy
- validation status
- promotion status
- rejection reason
- attempt count
- summary
- linked execution receipt ids

These receipts are suitable for audit, later memory use, and future governance layers.

## Integration Points

The main integration point is the failed-action path inside `backend/python/brain/runtime/orchestrator.py`.

After trusted execution returns a failed result:

- the orchestrator can build failure evidence
- self-repair can inspect the failure
- if the repair is promoted, the same action is replayed once
- if the repair is rejected or blocked, the original failure path remains intact
- a `runtime.self_repair.receipt` event is written to the execution audit stream

This keeps the current runtime architecture intact while adding a bounded recovery path.

## Conservative Defaults

The environment defaults are:

- `OMINI_ENABLE_SELF_REPAIR=false`
- `OMINI_SELF_REPAIR_ALLOW_PROMOTION=false`
- `OMINI_SELF_REPAIR_MAX_FILES=1`
- `OMINI_SELF_REPAIR_MAX_ATTEMPTS_PER_ACTION=1`
- `OMINI_SELF_REPAIR_MAX_RECURRENCE=2`
- `OMINI_SELF_REPAIR_ALLOWED_ROOT=backend/python/brain/runtime`

## Limitations

Phase 15 deliberately does not implement:

- unrestricted self-modification
- multi-file autonomous rewrites
- frontend or Rust self-repair
- architectural evolution
- persistent adaptive learning
- open-ended patch synthesis

The repair catalog is intentionally small and deterministic in this phase.

## How This Prepares Phases 16-20

Phase 15 establishes the minimum bounded recovery loop needed for future autonomy:

- failures become structured repair candidates
- repair attempts become policy-governed and auditable
- validated repairs become replayable actions instead of speculative ideas
- future phases can expand the repair catalog, governance depth, and learning quality without abandoning the trusted execution substrate

In short, Phase 15 makes Omni capable of disciplined, evidence-based, local recovery while remaining under strict control.

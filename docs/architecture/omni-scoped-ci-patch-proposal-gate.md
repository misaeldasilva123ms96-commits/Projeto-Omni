# Omni Scoped CI Patch Proposal Gate — Architecture

## Overview

Phase 33 adds the Scoped CI Patch Proposal Gate, which decides whether a safe
Phase 32 CI repair plan is eligible for a future scoped CI patch proposal
phase. It is a pure gate — it produces eligibility metadata only.

## Flow

```
Phase 32 CI Repair Planner  ──►  Phase 33 Scoped CI Patch Proposal Gate
                                       │
                                       ├─ disabled / dry_run / evaluate_patch_proposal / blocked
                                       │
                                       ├─ validate repair plan steps
                                       ├─ classify target areas / file roots
                                       ├─ validate validation commands (metadata only)
                                       ├─ enforce scope limits
                                       ├─ enforce attempt budget
                                       ├─ classify failure categories
                                       ├─ detect secrets
                                       └─ route next_allowed_phase:
                                            eligible  → scoped_ci_patch_proposal
                                            CI passed → merge_gate
                                            CI pending → wait_for_ci
                                            blocked    → human_review
```

## Source Files

| File | Purpose |
|---|---|
| `scoped_ci_patch_proposal_gate_types.py` | `ScopedCIPatchProposalGateRequest` / `ScopedCIPatchProposalGateResult` dataclasses |
| `scoped_ci_patch_proposal_gate_truth.py` | `ScopedCIPatchProposalGateEvidence` + builder + governance decision mapping |
| `scoped_ci_patch_proposal_gate.py` | `evaluate_scoped_ci_patch_proposal_gate()` entry function |

## Modes

- **disabled**: no eligibility evaluation; blocks immediately.
- **dry_run**: validates evidence, sets status dry_run, no eligibility.
- **evaluate_patch_proposal**: full evaluation if evidence passes all checks.
- **blocked**: blocks all eligibility.

## Validation

- Repair plan steps: allowed types (propose_scoped_*, inspect_*, request_human_review)
- Target areas: 6 allowed, 12+ blocked
- Validation commands: metadata only; safe vs blocked patterns
- Failure categories: 5 allowed, 13 blocked
- Scope limits: max files (1-10), max hunks (1-50), max per file (1-20)
- Attempt budget: max 1-10, default 3

## Safety

- All `can_*` action flags false.
- No subprocess, shell, eval, exec, gh, or provider calls.
- No patch proposals, hunks, patches, file writes, source inspection.
- No Git mutation, commits, pushes, PR updates, merges.
- No log downloads, workflow retry/trigger.
- Human intervention required for exception triggers.

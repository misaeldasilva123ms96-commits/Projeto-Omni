# Omni CI Repair Loop Gate Architecture

## Overview

The CI Repair Loop Gate is a metadata-only decision phase that determines
whether a failed or inconclusive CI result from the Controlled CI Monitor
(Phase 30) is eligible for a future autonomous repair loop.

```
Phase 30 (CI Monitor Result)
    |
    v
Phase 31 (CI Repair Loop Gate)
    |
    +---> Eligible   -> ci_repair_planner phase
    +---> CI passed  -> merge_gate phase
    +---> CI pending -> wait_for_ci phase
    +---> Blocked    -> human_review phase
```

## Components

- `ci_repair_loop_gate_types.py`: Input request and output result dataclasses.
- `ci_repair_loop_gate_truth.py`: Runtime Truth evidence builder.
- `ci_repair_loop_gate.py`: Core gate logic.
- `evaluate_ci_repair_loop_gate()`: Main entry function.

## Input

The primary input is `ci_monitor_result` from Phase 30. Optional supporting
evidence from Phase 29 (CI monitor gate), Phase 28 (PR creator), and
Phase 27 (PR creation gate) can also be provided.

## Output

The gate produces:

1. **`CIRepairLoopGateResult`**: Structured decision with eligibility,
   failure categories, repair scope, repair plan, and all action flags.
2. **Runtime Truth**: Aggregate evidence of type
   `sandbox.ci_repair_loop_gate.decision`.

## Safety

- All action flags (`can_start_repair_loop`, `can_download_logs`, etc.)
  are always `False`.
- Failure categories are classified using safe metadata matching only.
- Secret-like content is redacted and blocked.
- Attempt budgets are enforced.
- Protected branches and unsafe repositories are rejected.
- No subprocess, shell, network, Git, or file mutation.

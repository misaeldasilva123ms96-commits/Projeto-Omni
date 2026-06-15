# Omni Scoped CI Patch Proposal Engine — Architecture

## Overview

Phase 34 adds the Scoped CI Patch Proposal Engine, which converts clean Phase 33
gate eligibility and Phase 32 repair plan metadata into bounded scoped CI patch
proposal metadata. Proposal metadata only — no patches applied, no files written,
no code edited, no source inspected, no commands executed, no Git mutations,
no provider/agent/MCP calls.

## Flow

```
Phase 32 CI Repair Planner  ──►  Phase 33 Scoped CI Patch Proposal Gate
                                        │
                                        └─►  Phase 34 Scoped CI Patch Proposal Engine
                                                   │
                                                   ├─ disabled / dry_run / propose_patch / blocked
                                                   │
                                                   ├─ validate gate evidence
                                                   ├─ validate repair planner evidence
                                                   ├─ validate CI evidence
                                                   ├─ classify operations by failure category
                                                   ├─ classify target areas / file roots
                                                   ├─ validate repair steps
                                                   ├─ validate commands (metadata only)
                                                   ├─ enforce scope limits
                                                   ├─ enforce attempt budget
                                                   ├─ detect secrets
                                                   ├─ generate proposals / hunks (metadata only)
                                                   ├─ suggest follow-up tests
                                                   └─ produce Runtime Truth evidence
```

## Source Files

| File | Purpose |
|---|---|
| `scoped_ci_patch_proposal_engine_types.py` | `ScopedCIPatchProposalEngineRequest` / `ScopedCIPatchProposalEngineResult` dataclasses |
| `scoped_ci_patch_proposal_engine_truth.py` | `ScopedCIPatchProposalEngineEvidence` + builder + governance decision mapping |
| `scoped_ci_patch_proposal_engine.py` | `evaluate_scoped_ci_patch_proposal_engine()` entry function |

## Modes

- **disabled**: no proposal evaluation; blocks immediately.
- **dry_run**: validates evidence, generates proposal preview without marking created.
- **propose_patch**: full evaluation and proposal metadata generation.
- **blocked**: blocks all proposal generation.

## Validation

- Gate evidence: Phase 33 Runtime Truth must be clean (no patch_proposal_created,
  patch_hunks_generated, patch_applied, files_written, code_edited, etc.)
- Planner evidence: Phase 32 must be clean and ready
- CI evidence: must be failed (not passed, pending, or inconclusive)
- PR state: must be open (not merged, closed, locked, archived)
- Repository: must match expected, no shell chars
- Branch: must not be main, protected, or empty
- SHA: must be a valid SHA-1 or SHA-256 hex string
- Operations: mapped from failure categories (test_failure → modify_existing/add_test,
  typecheck/lint/format → modify_existing, build → modify_existing/add_test)
- Target areas: 6 allowed, 12+ blocked
- Validation commands: metadata only; safe vs blocked patterns
- Scope limits: max files (1-10), max hunks (1-50), max per file (1-20)
- Attempt budget: max 1-10, default 3

## Safety

- All `can_*` action flags false.
- No subprocess, shell, eval, exec, gh, or provider calls.
- No patch application, file writes, source inspection.
- No Git mutation, commits, pushes, PR updates, merges.
- No log downloads, workflow retry/trigger.
- Hunk metadata uses `after_intent` only; `before_context` and `proposed_snippet`
  are explicitly `None` unless provided as safe input.

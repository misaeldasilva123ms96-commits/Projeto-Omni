# Manifest-Driven Execution

## Purpose

The execution manifest is no longer only an observability artifact. In Phase 4 it becomes a bounded operational contract that influences runtime execution.

## What the manifest controls

- `chosen_strategy`
- `selected_tools`
- `step_plan`
- `fallback_strategy`
- `output_mode`
- `observability_tags`
- `safety_notes`

## Practical effect

The dispatcher and executors use the manifest to decide:

- which executor should run
- whether reasoning depth is acceptable
- whether node delegation is required
- which synthesis mode should be applied
- when a downgrade or fallback is safer

## Non-goals

The manifest is not an unrestricted autonomous planner. It remains a compact, serializable contract whose role is to constrain execution, not to invent new capabilities.


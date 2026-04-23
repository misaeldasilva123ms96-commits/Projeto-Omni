# Project Status

## Current status

Omni is not fully working yet.

This repository is open because the runtime is complex, partially functional, and still being debugged in public. The goal is not to pretend the system is finished. The goal is to make the current state understandable and improve it with evidence.

## What contributors should know

- The repository contains real runtime code across Rust, Python, and Node.
- Some execution paths are functional.
- Some paths are still compatibility-heavy or degraded.
- A response existing does not automatically mean the correct runtime path happened.

## Why this repo is open for debugging

Omni benefits from contributors who can help with:

- runtime boundary debugging
- execution-path recovery
- observability truthfulness
- reproducible tests
- documentation and contributor onboarding

## Main issues right now

- not every tool-capable prompt follows the strongest execution path consistently
- compatibility execution still plays a large role in the runtime
- local environment differences can affect action execution success
- some parts of the system are clearer in observability than in user-facing behavior

## Good places to start

- `README.md`
- `ARCHITECTURE.md`
- `docs/architecture/runtime-flow.md`
- `docs/audits/brain-runtime-flow-map.md`
- `docs/audits/brain-remediation-plan.md`

## Contribution posture

Contributors are welcome, especially if they:

- document what they observe
- keep changes small and test-backed
- preserve honest degraded-state reporting
- avoid hiding broken parts behind cosmetic success

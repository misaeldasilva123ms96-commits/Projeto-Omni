# Autonomous Verification Model

## Verification planning

`verificationPlanner.js` generates a verification plan before execution when large engineering context exists.

## Supported modes

- targeted tests
- full tests
- dependency health

## Live runtime behavior

`engineering_tools.py` exposes `verification_runner`, which executes the plan and returns:

- `ok`
- `verification_modes`
- `runs`
- `merge_readiness`

## Integration

Verification summaries are persisted into:

- checkpoint engineering data
- execution state
- run summaries
- `inspect_verification`
- PR-style summaries

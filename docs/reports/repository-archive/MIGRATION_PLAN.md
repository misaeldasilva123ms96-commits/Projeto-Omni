# Migration Plan

## Step-by-Step Order

1. Freeze architectural boundaries and define the brain-to-executor contract
2. Rewire the current Node adapter to the new fusion brain facade
3. Introduce provider abstraction and permission bridge
4. Introduce audit logging and session snapshotting
5. Package the selected `src.zip` QueryEngine subset for live use
6. Bind Rust tool execution loop to the contract instead of using manifest-only integration
7. Migrate persistent memory, session, and transcript storage boundaries
8. Add multi-agent execution contexts and scoped tool policies
9. Modularize Kairos as an optional feature package
10. Remove obsolete adapters and duplicate brains

## What To Port First

- QueryEngine-facing orchestration boundaries
- Rust permission and execution semantics
- Provider routing abstraction
- Observability and audit hooks

## Test After Each Phase

1. Runner contract acceptance
2. Provider selection logic
3. Permission authorization
4. Session snapshot generation
5. Transcript audit writing
6. End-to-end Node runner response path

## Rollback Strategy

- Keep the external runner entrypoint stable
- Treat `src/queryEngineRunnerAdapter.js` as a compatibility shim
- If a phase destabilizes responses, restore the shim to the previous implementation and keep the new modules isolated behind tests

## Stabilization Checklist

- [ ] Contract schema stays backward-compatible
- [ ] Rust, Python, and frontend entrypoints remain unchanged
- [ ] Tool execution is always auditable
- [ ] Destructive tools require explicit policy handling
- [ ] No duplicate brain authority remains active
- [ ] Kairos remains optional

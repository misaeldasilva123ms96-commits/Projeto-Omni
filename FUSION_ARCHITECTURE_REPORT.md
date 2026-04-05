# Fusion Architecture Report

## Executive Summary

Projeto-Omni now has a first-pass fusion architecture that clearly separates:

- `src.zip` as the primary cognitive brain reference
- `claw-code-main.zip` Rust runtime as execution authority
- `openclaude-main.zip` as provider and platform integration layer
- Kairos as an optional deferred feature layer

The initial implementation does not blindly merge all codebases. It introduces a maintainable contract-driven structure inside this repository, rewires the active Node runner to a new fusion brain facade, and preserves the existing external architecture:

Frontend React -> Rust API -> Python Orchestrator -> Node Runtime

## Source Repo Assessment

| Component | Source Repo | Purpose | Maturity | Decision |
| --- | --- | --- | --- | --- |
| `QueryEngine.ts` | `src.zip` | Best cognitive orchestrator and task loop | High | Keep as main brain reference |
| TypeScript tool orchestration | `src.zip` | Rich tool routing, MCP, sessions, state | High | Keep and adapt |
| Rust conversation runtime | `claw-code-main.zip` | Real execution loop, tool-use cycle | High | Keep as execution authority |
| Rust permission policy | `claw-code-main.zip` | Safe authorization before tool execution | High | Keep and mirror in JS bridge |
| Rust session/usage tracking | `claw-code-main.zip` | Reliable runtime bookkeeping | High | Keep and target for deeper migration |
| Provider bootstrap and profiles | `openclaude-main.zip` | Provider abstraction and CLI bootstrap | High | Keep as provider/platform layer |
| Python smart router | `openclaude-main.zip` | Multi-provider routing logic | Medium | Keep patterns, wrap selectively |
| Existing project JS adapter | `project/src` | Thin runner adapter | Low | Replace as brain authority, preserve only as shim |
| Existing project Rust API shell | `project/backend/rust` | API ingress and Python handoff | Medium | Keep for compatibility, evolve later |
| Kairos/proactive flows | `openclaude-main.zip` | Scheduled/proactive assistance | Medium | Defer into optional feature layer |

## Selected Architecture

- Main brain: TypeScript QueryEngine lineage from `src.zip`
- Execution runtime: Rust runtime patterns from `claw-code-main.zip`
- Provider layer: OpenClaude profile/provider routing patterns
- Optional future layer: Kairos and proactive workflows

## Rejected or Deferred Pieces

- Duplicate brains where Python and TypeScript both act as top-level cognition
- Summary-only adapters that narrate plans instead of executing tasks
- Kairos as a core orchestration dependency before the execution contract is stable
- Duplicate memory systems without a clear ownership boundary

## Migration Risks

1. The current repository still uses a lightweight JS runtime for active execution, so deeper TypeScript QueryEngine adoption needs an incremental transpilation or packaging strategy.
2. Rust execution authority is documented and contract-aligned, but not yet fully embedded into the live API loop.
3. Provider routing is wrapped at the abstraction layer, but not yet calling OpenClaude upstream code directly at runtime.

## Roadmap

1. Stabilize the brain-to-executor contract and audit logging
2. Package or transpile the selected QueryEngine subset from `src.zip`
3. Move tool execution and permission enforcement into Rust runtime modules
4. Replace heuristic provider router with the selected OpenClaude routing path
5. Migrate persistent memory, sessions, and transcripts into the layered storage model
6. Enable Kairos only after the core path is stable and observable

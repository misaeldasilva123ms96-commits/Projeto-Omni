# Repository Component Mapping

## Main Cognitive Brain Candidates

| Component | Source | File(s) | Assessment | Decision |
| --- | --- | --- | --- | --- |
| QueryEngine | `src.zip` | `src/QueryEngine.ts` | Richest orchestration lifecycle, tool loop, memory injection, session continuity | Keep as main brain reference |
| Extracted QueryEngine authority | `project` adapted from `src.zip` | `core/brain/queryEngineAuthority.js` | Active authoritative cognitive kernel for local runtime | Keep |
| QueryEngine adapter | `src.zip` | `src/queryEngineRunnerAdapter.js` | Useful as compatibility bridge, but weaker than full QueryEngine | Adapt selectively |
| QueryEngine | `openclaude-main.zip` | `src/QueryEngine.ts` | Similar lineage, more product/platform coupling | Use patterns, not as primary authority |
| Python QueryEngine | `claw-code-main.zip` | `src/query_engine.py` | Lightweight mirrored runtime, not strongest planner | Discard as main brain |

## Agent Systems / Multi-Agent / Delegation

| Component | Source | File(s) | Assessment | Decision |
| --- | --- | --- | --- | --- |
| Agent definitions and subagent support | `src.zip` | `src/tools/AgentTool/*`, `src/QueryEngine.ts` | Strong specialist delegation model | Keep as specialist layer |
| Swarm / teammate patterns | `openclaude-main.zip` | `src/utils/swarm/*`, `src/main.tsx` | Mature UX and coordination patterns | Adapt for future expansion |
| Parallel competing brains | multiple | various | Risky and confusing | Reject |

## Memory / Sessions / Transcripts

| Component | Source | File(s) | Assessment | Decision |
| --- | --- | --- | --- | --- |
| Session storage and transcript hooks | `src.zip` | `src/utils/sessionStorage.js`, `src/assistant/sessionHistory.ts` | Strong session continuity and transcript-facing UX | Keep patterns |
| Memdir / memory prompt loading | `src.zip` | `src/memdir/*` | Good memory injection mechanism | Keep patterns |
| Rust typed session model | `claw-code-main.zip` | `rust/crates/runtime/src/session.rs` | Strongest session schema and persistence model | Keep as execution/session truth |
| Runtime compaction and usage | `claw-code-main.zip` | `rust/crates/runtime/src/compact.rs`, `usage.rs` | Production-grade runtime bookkeeping | Keep |

## Execution Runtime / Permissions

| Component | Source | File(s) | Assessment | Decision |
| --- | --- | --- | --- | --- |
| Conversation runtime loop | `claw-code-main.zip` | `rust/crates/runtime/src/conversation.rs` | Best real execution loop found | Keep as execution authority |
| Permission policy | `claw-code-main.zip` | `rust/crates/runtime/src/permissions.rs` | Clear allow/deny/prompt model | Keep |
| Rust executor bridge | `project` adapted from `claw-code-main.zip` | `backend/rust/src/bin/executor_bridge.rs` | Active narrow real execution bridge using selected runtime crate exports | Keep |
| Python-to-Rust execution bridge | `project` adapted around `claw-code-main.zip` | `backend/python/brain/runtime/rust_executor_bridge.py`, `backend/python/brain/runtime/orchestrator.py` | Active live bridge for this host; preserves Rust as execution authority while bypassing direct Node spawn limitations | Keep |
| OpenClaude permission system | `openclaude-main.zip` | `src/utils/permissions/*` | Very rich, but platform-coupled and broad | Adapt selected policies only |

## Providers / CLI / Codex

| Component | Source | File(s) | Assessment | Decision |
| --- | --- | --- | --- | --- |
| Provider bootstrap | `openclaude-main.zip` | `scripts/provider-bootstrap.ts` | Best provider setup and routing UX | Keep |
| Provider config | `openclaude-main.zip` | `src/services/api/providerConfig.ts/js`, `src/utils/providerProfile.ts` | Strong provider abstraction | Keep |
| Smart router | `openclaude-main.zip` | `python/smart_router.py` | Good provider selection pattern | Adapt selectively |
| Codex compatibility | `openclaude-main.zip` | provider config/profile flow | Strong platform integration | Keep |

## Kairos / Proactive Layer

| Component | Source | File(s) | Assessment | Decision |
| --- | --- | --- | --- | --- |
| Assistant / Kairos gate | `openclaude-main.zip` | `src/main.tsx`, `src/assistant/*` | Valuable advanced layer, but not core runtime | Defer to optional feature |

## Selected Ownership

- Main brain: `src.zip`
- Execution runtime: Rust from `claw-code-main.zip`
- Provider/platform layer: `openclaude-main.zip`
- Optional advanced layer: Kairos
- Specialist delegation layer: extracted from `src.zip` / `openclaude` agent patterns

## Explicitly Rejected

- Any design where Python and TypeScript both act as the main brain
- Duplicate query engines with no single authority
- Fake execution layers that narrate actions instead of performing them
- Blind code merge across all three repositories

## Deprecated Runtime Authorities

- `core/brain/fusionBrain.js` as a heuristic authority: deprecated, now facade only
- local heuristic execution inside the original phase-1 fusion path: deprecated
- direct Node child-process Rust execution in this host: transitional and not authoritative
- `runtime/execution/rustExecutorBridge.js` as the primary live path: transitional only on this host

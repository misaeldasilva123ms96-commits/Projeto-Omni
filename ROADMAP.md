# Omni Open Source Roadmap

## Phase 1 — Organization

Goal:
Make the repository understandable, navigable, and contributor-friendly.

Expected outcome:
Clear entrypoint documents, a cleaner repository layout, and a public-facing explanation of what Omni is and what is still broken.

## Phase 2 — Public Debug

Goal:
Open the current runtime state to contributors with honest debugging artifacts and reproducible runtime evidence.

Expected outcome:
Contributors can inspect failures, understand current limitations, and work from real runtime traces instead of assumptions.

## Phase 3 — Execution Recovery

Goal:
Recover stable end-to-end execution paths for tool-capable requests.

Expected outcome:
More requests complete through real execution rather than degrading into planning-only or compatibility-heavy paths.

## Phase 4 — Runtime Truth

Goal:
Make runtime inspection and provenance always reflect what actually happened.

Expected outcome:
Shortcut, bridge, compatibility, action execution, and fallback paths are clearly distinguishable in the public and internal runtime signals.

## Phase 5 — Stability

Goal:
Reduce runtime fragility across Rust, Python, Node, and local tool execution.

Expected outcome:
A more repeatable development environment, fewer transport regressions, and better reliability under normal contributor setup.

## Phase 6 — Cognitive Validation

Goal:
Prove that Omni is executing a real cognitive flow rather than only producing plausible responses.

Expected outcome:
Representative prompts show stable, inspectable, tool-backed runtime behavior with useful memory, observability, and fallback semantics.

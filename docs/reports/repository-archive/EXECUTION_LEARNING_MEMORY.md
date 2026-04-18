# Execution Learning Memory

## Entry types
- success
- failure_avoidance
- execution_pattern
- retry outcome lessons

## Write rules
- Entries are explicit and structured.
- Reflection can write a lesson after a hierarchical or weak run.
- Entries are linked to session, task, run, and transcript references.
- The store is capped and deduplicated by entry id.

## Retrieval rules
- Retrieval is bounded by archetype, tool family, token overlap, and confidence.
- Retrieval is used before planning in the Node cognitive authority.

## Runtime influence
- Learning matches are injected into planner context.
- They can bias planning toward safer inspection-first strategies.
- They can reinforce failure-avoidance behavior such as not retrying blocked mutations.

## Audit lineage
- File: `.logs/fusion-runtime/execution-learning-memory.json`
- Event: `runtime.learning_memory.updated`

# Memory Architecture

## Layers

### Session Memory

- Source: recent history and session transcript context
- Owner: `core/memory/memoryLayers.js`
- Purpose: preserve the near conversational window

### Working / Task Memory

- Source: `.logs/fusion-runtime/runtime-memory-store.json`
- Owner: `storage/memory/runtimeMemoryStore.js`
- Purpose:
  - last artifact used
  - recent artifacts
  - active runtime mode
  - latest task-oriented context

### Persistent Long-Term Memory

- Source: Python memory store + runtime memory persistent envelope
- Purpose:
  - name
  - work
  - stable preferences/objectives

### Semantic Memory

- Owner: `storage/memory/semanticMemory.js`
- Place in store: `semantic.candidates`
- Purpose:
  - semantically rank prior artifacts and runtime outputs
  - improve context retrieval before planning
  - blend relevance with recency and session context

Current truth:

- semantic retrieval is live
- it is not embedding-backed yet
- it already affects plan selection in the runtime path

## Retrieval Policy

Before planning:

1. hydrate session memory from recent turns
2. hydrate persistent user facts
3. hydrate working memory from runtime store
4. query semantic matches for the current user request
5. derive retrieval context in `memorySpecialist`

Current retrieval bias:

- prefer semantic artifact match when the request strongly aligns with prior work
- prefer recent artifact when the user explicitly implies continuation
- prefer persistent facts for identity/work recall
- keep session memory short and recent

## Write Policy

Persistent writes:

- only stable user facts such as name/work should become persistent automatically

Working memory writes:

- last artifact used
- recent artifacts
- last runtime mode / last intent

Semantic writes:

- meaningful runtime artifacts and summaries can become semantic candidates
- semantic writes stay scoped by session and transcript-linked runtime context

Transcript-linked writes:

- runtime transcript captures step outputs
- Python transcripts capture user/assistant turns

## Indexing Strategy

- runtime memory store keeps per-session envelopes
- artifacts are indexed by session and ordered by recency
- semantic candidates are ranked at query time
- transcript files remain append-only JSONL

## Lifecycle Integration Points

- retrieval before planning: `core/brain/queryEngineAuthority.js`
- semantic query and ranking: `storage/memory/runtimeMemoryStore.js`
- retrieval enrichment: `features/multiagent/specialists/memorySpecialist.js`
- plan targeting: `features/multiagent/specialists/plannerSpecialist.js`
- runtime result synchronization: `backend/python/brain/runtime/orchestrator.py`
- snapshot summarization: `storage/memory/memoryPersistence.js`

## Limitations

- no embedding backend yet
- similarity is lightweight and token-based
- semantic memory is strongest for artifact/task retrieval, not world-knowledge reasoning

## Future Hook Points

- provider-backed embedding generation
- vector-backed candidate storage
- evaluator-informed ranking adjustments
- semantic write suppression for low-value records

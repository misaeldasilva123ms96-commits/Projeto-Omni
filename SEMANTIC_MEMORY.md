# Semantic Memory

## Embedding Path

Current live strategy:

- lightweight lexical-semantic scoring via [`storage/memory/semanticMemory.js`](./storage/memory/semanticMemory.js)
- no dense vector backend yet
- the interface is intentionally modular so a future embedding provider can replace the scorer without changing the outer runtime flow

## Retrieval Flow

1. runtime artifacts are recorded after execution
2. semantic entries are created from:
   - path
   - preview
   - content/message context when available
3. on a new user query, `findSemanticMatches(...)` ranks candidates
4. `memorySpecialist` injects the best semantic match into retrieval context
5. `plannerSpecialist` can pick the matched artifact path even when the user did not name the file directly

## Ranking Policy

Current score blends:

- semantic similarity via token overlap
- recency score
- task/path boost when the query mentions a candidate path directly

## Indexing / Storage Strategy

Store:

- `.logs/fusion-runtime/runtime-memory-store.json`

Semantic envelope:

- `semantic.candidates`
- `semantic.last_query`
- `semantic.last_matches`

## Write Rules

- only execution-grounded artifacts become semantic entries
- semantic writes are bounded to recent/high-value artifacts
- the system does not write arbitrary user text into semantic memory without runtime grounding

## Runtime Integration Points

- candidate creation: `recordRuntimeArtifacts(...)`
- ranking: `findSemanticMatches(...)`
- retrieval injection: [`features/multiagent/specialists/memorySpecialist.js`](./features/multiagent/specialists/memorySpecialist.js)
- planning influence: [`features/multiagent/specialists/plannerSpecialist.js`](./features/multiagent/specialists/plannerSpecialist.js)

## Limitations

- similarity is token-based, not embedding-based
- no ANN/vector store yet
- no cross-session semantic federation yet

## Future Evolution

- provider-backed embeddings
- local vector store
- hybrid ranking with transcript/task priors

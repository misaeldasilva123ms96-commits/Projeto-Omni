# Vector Memory

## Embedding Path

The live embedding path is currently local and deterministic:

- adapter: `storage/memory/embeddingAdapter.js`
- model: `local-hash-embedding-v1`
- dimensions: `48`

This is a real vector path, not a placeholder. It gives the runtime embedding-backed retrieval without forcing an external provider dependency in this phase.

## Storage Design

Runtime vector memory is persisted in:

- `.logs/fusion-runtime/runtime-memory-store.json`

Each semantic candidate stores:

- `path`
- `preview`
- `source`
- `embedding_text`
- `embedding`
- `updated_at`
- `session_relevance`
- `transcript_ref`

## Ranking Logic

Candidate ranking blends:

1. vector similarity
2. lexical relevance
3. recency
4. session/task relevance

## Write And Dedup Policy

Semantic writes are intentional and bounded:

- runtime artifacts feed semantic entry creation
- candidates are deduplicated by path + preview
- only a bounded recent set is kept in the envelope

## Runtime Integration

The live path is:

1. `queryEngineAuthority.js` asks `findSemanticMatches(...)`
2. semantic matches influence retrieval context
3. the planner uses that context for file/step selection
4. Python audit logs emit `runtime.vector.retrieval`

## Fallback Behavior

If vector retrieval is unavailable or empty:

- the runtime still has lexical/recency retrieval
- memory recall can still fall back to recent artifacts

## Limitations

- local hashed embeddings are weaker than provider-backed semantic embeddings
- no ANN/vector database is used yet
- ranking is file-backed today

## Future Evolution

Next upgrades are intentionally modular:

- provider-backed embeddings behind the same adapter contract
- optional vector database or ANN index
- stronger hybrid reranking using execution intent and transcript salience

const { cosineSimilarity, describeEmbeddingMode, generateEmbedding, tokenize } = require('./embeddingAdapter');

function jaccardScore(left, right) {
  const leftTokens = new Set(tokenize(left));
  const rightTokens = new Set(tokenize(right));
  if (leftTokens.size === 0 || rightTokens.size === 0) {
    return 0;
  }
  const intersection = [...leftTokens].filter(token => rightTokens.has(token)).length;
  const union = new Set([...leftTokens, ...rightTokens]).size;
  return union === 0 ? 0 : intersection / union;
}

function recencyScore(isoTimestamp) {
  if (!isoTimestamp) return 0.1;
  const ageMs = Math.max(0, Date.now() - Date.parse(isoTimestamp));
  const ageHours = ageMs / (1000 * 60 * 60);
  return Math.max(0.1, 1 - Math.min(1, ageHours / 24));
}

function taskRelevanceScore(query, candidate) {
  const normalizedQuery = String(query || '').toLowerCase();
  const pathText = String(candidate?.path || '').toLowerCase();
  const sourceText = String(candidate?.source || '').toLowerCase();
  let score = 0;
  if (pathText && normalizedQuery.includes(pathText)) score += 0.25;
  if (sourceText && normalizedQuery.includes(sourceText)) score += 0.1;
  if (candidate?.session_relevance) score += Number(candidate.session_relevance) || 0;
  return Number(Math.min(0.35, score).toFixed(4));
}

function buildSemanticDocument({ path, preview, message, content }) {
  return [path, preview, message, content].filter(Boolean).join('\n');
}

function buildSemanticEntry(entry = {}) {
  const embeddingText = buildSemanticDocument({
    path: entry.path,
    preview: entry.preview,
    message: entry.message,
    content: entry.content,
  });
  return {
    path: entry.path || '',
    preview: entry.preview || '',
    source: entry.source || 'runtime',
    embedding_text: embeddingText,
    embedding: entry.embedding || generateEmbedding(embeddingText),
    updated_at: entry.updated_at || new Date().toISOString(),
    session_relevance: Number(entry.session_relevance || 0),
    transcript_ref: entry.transcript_ref || null,
  };
}

function dedupeSemanticCandidates(candidates = [], limit = 24) {
  const seen = new Set();
  const deduped = [];
  for (const candidate of candidates) {
    const key = `${candidate.path || ''}::${candidate.preview || ''}`;
    if (!candidate.path || seen.has(key)) continue;
    seen.add(key);
    deduped.push(candidate);
    if (deduped.length >= limit) break;
  }
  return deduped;
}

function rankSemanticCandidates({ query, candidates = [], limit = 3, queryEmbedding = null }) {
  const liveQueryEmbedding = queryEmbedding || generateEmbedding(query);
  return candidates
    .map(candidate => {
      const relevance = jaccardScore(query, candidate.embedding_text || candidate.preview || candidate.path || '');
      const vectorSimilarity = cosineSimilarity(liveQueryEmbedding, candidate.embedding || generateEmbedding(candidate.embedding_text || ''));
      const recency = recencyScore(candidate.updated_at);
      const taskBoost = taskRelevanceScore(query, candidate);
      const score = Number((vectorSimilarity * 0.5 + relevance * 0.25 + recency * 0.15 + taskBoost * 0.1).toFixed(4));
      return {
        ...candidate,
        retrieval_score: score,
        vector_score: Number(vectorSimilarity.toFixed(4)),
        relevance_score: Number(relevance.toFixed(4)),
        recency_score: Number(recency.toFixed(4)),
        task_score: taskBoost,
      };
    })
    .filter(candidate => candidate.retrieval_score > 0.12)
    .sort((left, right) => right.retrieval_score - left.retrieval_score)
    .slice(0, limit);
}

module.exports = {
  buildSemanticEntry,
  buildSemanticDocument,
  dedupeSemanticCandidates,
  describeEmbeddingMode,
  jaccardScore,
  rankSemanticCandidates,
  tokenize,
};

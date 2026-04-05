function tokenize(text) {
  return String(text || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean);
}

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

function buildSemanticDocument({ path, preview, message, content }) {
  return [path, preview, message, content].filter(Boolean).join('\n');
}

function rankSemanticCandidates({ query, candidates = [], limit = 3 }) {
  return candidates
    .map(candidate => {
      const relevance = jaccardScore(query, candidate.embedding_text || candidate.preview || candidate.path || '');
      const recency = recencyScore(candidate.updated_at);
      const taskBoost = String(query || '').toLowerCase().includes(String(candidate.path || '').toLowerCase()) ? 0.2 : 0;
      const score = Number((relevance * 0.65 + recency * 0.25 + taskBoost).toFixed(4));
      return {
        ...candidate,
        retrieval_score: score,
        relevance_score: Number(relevance.toFixed(4)),
        recency_score: Number(recency.toFixed(4)),
      };
    })
    .filter(candidate => candidate.retrieval_score > 0)
    .sort((left, right) => right.retrieval_score - left.retrieval_score)
    .slice(0, limit);
}

module.exports = {
  buildSemanticDocument,
  jaccardScore,
  rankSemanticCandidates,
  tokenize,
};

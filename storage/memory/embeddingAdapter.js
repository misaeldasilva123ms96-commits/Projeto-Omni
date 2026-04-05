const DEFAULT_EMBEDDING_MODEL = 'local-hash-embedding-v1';
const DEFAULT_DIMENSIONS = 48;

function tokenize(text) {
  return String(text || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean);
}

function hashToken(token, dimensions) {
  let hash = 2166136261;
  for (const char of token) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash) % dimensions;
}

function normalizeVector(vector) {
  const magnitude = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0));
  if (!magnitude) {
    return vector.map(() => 0);
  }
  return vector.map(value => Number((value / magnitude).toFixed(6)));
}

function generateEmbedding(text, options = {}) {
  const dimensions = Number(options.dimensions || DEFAULT_DIMENSIONS);
  const model = String(options.model || DEFAULT_EMBEDDING_MODEL);
  const vector = new Array(dimensions).fill(0);
  const tokens = tokenize(text);

  for (const token of tokens) {
    const index = hashToken(token, dimensions);
    vector[index] += 1;
  }

  return {
    model,
    dimensions,
    vector: normalizeVector(vector),
    token_count: tokens.length,
  };
}

function cosineSimilarity(leftEmbedding, rightEmbedding) {
  const leftVector = leftEmbedding?.vector || [];
  const rightVector = rightEmbedding?.vector || [];
  if (!Array.isArray(leftVector) || !Array.isArray(rightVector) || leftVector.length === 0 || rightVector.length === 0) {
    return 0;
  }

  const dimensions = Math.min(leftVector.length, rightVector.length);
  let dot = 0;
  for (let index = 0; index < dimensions; index += 1) {
    dot += Number(leftVector[index] || 0) * Number(rightVector[index] || 0);
  }

  return Number(Math.max(0, Math.min(1, dot)).toFixed(6));
}

function describeEmbeddingMode() {
  return {
    mode: 'local-vector',
    model: DEFAULT_EMBEDDING_MODEL,
    dimensions: DEFAULT_DIMENSIONS,
    provider: 'local',
  };
}

module.exports = {
  DEFAULT_DIMENSIONS,
  DEFAULT_EMBEDDING_MODEL,
  cosineSimilarity,
  describeEmbeddingMode,
  generateEmbedding,
  tokenize,
};

const fs = require('fs');
const path = require('path');
const {
  buildSemanticEntry,
  dedupeSemanticCandidates,
  describeEmbeddingMode,
  rankSemanticCandidates,
} = require('./semanticMemory');

function getStorePath(cwd) {
  const dir = path.join(cwd, '.logs', 'fusion-runtime');
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, 'runtime-memory-store.json');
}

function loadRuntimeMemory(cwd) {
  const storePath = getStorePath(cwd);
  try {
    return JSON.parse(fs.readFileSync(storePath, 'utf8'));
  } catch {
    return { sessions: {} };
  }
}

function saveRuntimeMemory(cwd, store) {
  const storePath = getStorePath(cwd);
  fs.writeFileSync(storePath, JSON.stringify(store, null, 2), 'utf8');
  return storePath;
}

function ensureEnvelope(store, sessionId) {
  store.sessions = store.sessions || {};
  const existing = store.sessions[sessionId] || {};
  const envelope = {
    session: existing.session || {},
    working: existing.working || {},
    persistent: existing.persistent || {},
    semantic: existing.semantic || { candidates: [], last_query: '', last_matches: [] },
  };
  store.sessions[sessionId] = envelope;
  return envelope;
}

function flattenEnvelope(envelope) {
  return {
    ...envelope.persistent,
    ...envelope.working,
    semantic_candidates: Array.isArray(envelope.semantic?.candidates) ? envelope.semantic.candidates : [],
    semantic_last_matches: Array.isArray(envelope.semantic?.last_matches) ? envelope.semantic.last_matches : [],
    vector_mode: envelope.semantic?.vector_mode || describeEmbeddingMode(),
  };
}

function getSessionMemoryEnvelope(cwd, sessionId) {
  const store = loadRuntimeMemory(cwd);
  const envelope = ensureEnvelope(store, sessionId);
  return JSON.parse(JSON.stringify(envelope));
}

function getSessionRuntimeMemory(cwd, sessionId) {
  const envelope = getSessionMemoryEnvelope(cwd, sessionId);
  return flattenEnvelope(envelope);
}

function updateSessionRuntimeMemory(cwd, sessionId, patch) {
  const store = loadRuntimeMemory(cwd);
  const envelope = ensureEnvelope(store, sessionId);

  envelope.persistent = {
    ...envelope.persistent,
    ...patch,
    updated_at: new Date().toISOString(),
  };
  envelope.session = {
    ...envelope.session,
    updated_at: new Date().toISOString(),
  };

  saveRuntimeMemory(cwd, store);
  return flattenEnvelope(envelope);
}

function recordRuntimeArtifacts(cwd, sessionId, artifacts = []) {
  const store = loadRuntimeMemory(cwd);
  const envelope = ensureEnvelope(store, sessionId);
  const recent = Array.isArray(envelope.working.recent_artifacts)
    ? envelope.working.recent_artifacts
    : [];

  const merged = [...artifacts, ...recent]
    .filter(item => item && typeof item.path === 'string' && item.path)
    .slice(0, 12);

  envelope.working = {
    ...envelope.working,
    last_artifact: merged[0] || envelope.working.last_artifact || null,
    recent_artifacts: merged,
    updated_at: new Date().toISOString(),
  };

  for (const artifact of merged.slice(0, 4)) {
    recordSemanticEntry(cwd, sessionId, {
      path: artifact.path,
      preview: artifact.preview || '',
      source: artifact.kind || 'artifact',
    });
  }

  saveRuntimeMemory(cwd, store);
  return flattenEnvelope(envelope);
}

function recordSemanticEntry(cwd, sessionId, entry = {}) {
  const store = loadRuntimeMemory(cwd);
  const envelope = ensureEnvelope(store, sessionId);
  const candidates = Array.isArray(envelope.semantic.candidates) ? envelope.semantic.candidates : [];
  const normalizedEntry = buildSemanticEntry(entry);
  envelope.semantic.vector_mode = describeEmbeddingMode();
  envelope.semantic.candidates = dedupeSemanticCandidates([normalizedEntry, ...candidates], 24);
  saveRuntimeMemory(cwd, store);
  return flattenEnvelope(envelope);
}

function findSemanticMatches(cwd, sessionId, query, limit = 3) {
  const store = loadRuntimeMemory(cwd);
  const envelope = ensureEnvelope(store, sessionId);
  const matches = rankSemanticCandidates({
    query,
    candidates: Array.isArray(envelope.semantic.candidates) ? envelope.semantic.candidates : [],
    limit,
  });
  envelope.semantic.last_query = query;
  envelope.semantic.last_matches = matches;
  envelope.semantic.last_query_embedding = matches.length > 0
    ? matches[0].embedding?.model || describeEmbeddingMode().model
    : describeEmbeddingMode().model;
  envelope.semantic.vector_mode = describeEmbeddingMode();
  saveRuntimeMemory(cwd, store);
  return matches;
}

function updateWorkingMemory(cwd, sessionId, patch) {
  const store = loadRuntimeMemory(cwd);
  const envelope = ensureEnvelope(store, sessionId);
  envelope.working = {
    ...envelope.working,
    ...patch,
    updated_at: new Date().toISOString(),
  };
  saveRuntimeMemory(cwd, store);
  return flattenEnvelope(envelope);
}

module.exports = {
  getSessionMemoryEnvelope,
  getSessionRuntimeMemory,
  loadRuntimeMemory,
  findSemanticMatches,
  recordSemanticEntry,
  recordRuntimeArtifacts,
  saveRuntimeMemory,
  updateSessionRuntimeMemory,
  updateWorkingMemory,
};

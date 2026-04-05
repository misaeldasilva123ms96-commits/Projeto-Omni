function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function buildRetrievalContext({ message, memoryLayers, runtimeMemory, semanticMatches = [] }) {
  const text = normalizeText(message);
  const recentArtifacts = Array.isArray(runtimeMemory?.recent_artifacts)
    ? runtimeMemory.recent_artifacts
    : [];

  return {
    session_summary: memoryLayers?.working?.summary || '',
    active_constraints: memoryLayers?.working?.active_constraints || [],
    known_name: runtimeMemory?.nome || memoryLayers?.long_term?.nome || '',
    known_work: runtimeMemory?.trabalho || memoryLayers?.long_term?.trabalho || '',
    last_artifact: runtimeMemory?.last_artifact || recentArtifacts[0] || null,
    recent_artifacts: recentArtifacts,
    semantic_candidates: Array.isArray(runtimeMemory?.semantic_candidates)
      ? runtimeMemory.semantic_candidates
      : [],
    semantic_match: Array.isArray(semanticMatches) && semanticMatches.length > 0 ? semanticMatches[0] : null,
    semantic_matches: semanticMatches,
    prefers_recent_artifact: text.includes('de novo') || text.includes('novamente'),
  };
}

function enrichWithMemory({ message, memoryLayers, runtimeMemory, semanticMatches = [] }) {
  const text = normalizeText(message);
  const retrievalContext = buildRetrievalContext({
    message,
    memoryLayers,
    runtimeMemory,
    semanticMatches,
  });

  const hints = {
    known_name: retrievalContext.known_name,
    known_work: retrievalContext.known_work,
    retrieval_context: retrievalContext,
  };

  const nameMatch = String(message).match(/meu nome [ée]\s+([^,.]+)/i);
  if (nameMatch) {
    hints.new_name = nameMatch[1].trim();
  }

  const workMatch = String(message).match(/eu trabalho com\s+([^,.]+)/i);
  if (workMatch) {
    hints.new_work = workMatch[1].trim();
  }

  if (retrievalContext.prefers_recent_artifact && retrievalContext.last_artifact?.path) {
    hints.recalled_artifact_path = retrievalContext.last_artifact.path;
  }
  if (!hints.recalled_artifact_path && retrievalContext.semantic_match?.path) {
    hints.recalled_artifact_path = retrievalContext.semantic_match.path;
  }

  return hints;
}

module.exports = {
  buildRetrievalContext,
  enrichWithMemory,
};

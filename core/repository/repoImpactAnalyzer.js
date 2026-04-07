const path = require('path');

function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function tokenizeMessage(message) {
  return Array.from(new Set(
    normalizeText(message)
      .split(/[^a-z0-9_./-]+/)
      .map(token => token.trim())
      .filter(token => token.length >= 3),
  ));
}

function inferHotspots(repositoryAnalysis) {
  const dependencyGraph = Array.isArray(repositoryAnalysis?.dependency_graph) ? repositoryAnalysis.dependency_graph : [];
  return dependencyGraph
    .map(item => ({
      path: item.file,
      import_count: Array.isArray(item.imports) ? item.imports.length : 0,
    }))
    .sort((left, right) => right.import_count - left.import_count)
    .slice(0, 8);
}

function pickModuleCandidates(repositoryAnalysis, message) {
  const fileIndex = Array.isArray(repositoryAnalysis?.file_index) ? repositoryAnalysis.file_index : [];
  const tokens = tokenizeMessage(message);
  const hotspots = inferHotspots(repositoryAnalysis);
  const hotspotSet = new Set(hotspots.map(item => item.path));

  return fileIndex
    .filter(item => typeof item?.path === 'string' && !item.path.startsWith('vendor/'))
    .map(item => {
      const normalizedPath = normalizeText(item.path);
      const basename = normalizeText(path.basename(item.path, path.extname(item.path)));
      let score = 0;
      for (const token of tokens) {
        if (normalizedPath.includes(token)) score += 3;
        if (basename === token) score += 2;
      }
      if (hotspotSet.has(item.path)) score += 2;
      if (['typescript', 'javascript', 'python', 'rust'].includes(String(item.language))) score += 1;
      return {
        path: item.path,
        language: item.language,
        score,
        hotspot: hotspotSet.has(item.path),
      };
    })
    .filter(item => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 12);
}

function pickTestCandidates(repositoryAnalysis, moduleCandidates) {
  const fileIndex = Array.isArray(repositoryAnalysis?.file_index) ? repositoryAnalysis.file_index : [];
  const moduleTokens = moduleCandidates.flatMap(item => {
    const base = path.basename(item.path, path.extname(item.path));
    return [base, base.replace(/^test[_-]?/, '')].filter(Boolean);
  });
  const tokenSet = new Set(moduleTokens.map(item => normalizeText(item)));
  return fileIndex
    .filter(item => typeof item?.path === 'string' && /(^tests\/|test|spec)/i.test(item.path))
    .map(item => {
      const normalizedPath = normalizeText(item.path);
      let score = 0;
      for (const token of tokenSet) {
        if (normalizedPath.includes(token)) score += 2;
      }
      if (score === 0 && normalizedPath.includes('test')) score = 1;
      return {
        path: item.path,
        language: item.language,
        score,
      };
    })
    .filter(item => item.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 8);
}

function buildIntegrationRiskSummary(repositoryAnalysis, moduleCandidates, hotspots) {
  const frameworks = Array.isArray(repositoryAnalysis?.repository_map?.frameworks)
    ? repositoryAnalysis.repository_map.frameworks
    : [];
  const riskFlags = [];
  if (frameworks.length >= 3) riskFlags.push('multi-runtime-repository');
  if (moduleCandidates.length >= 6) riskFlags.push('wide-module-surface');
  if (hotspots.length >= 4) riskFlags.push('hotspot-coupling');
  return {
    risk_level: riskFlags.length >= 3 ? 'high' : riskFlags.length >= 1 ? 'medium' : 'low',
    flags: riskFlags,
    summary: riskFlags.length > 0
      ? `Detected integration risks: ${riskFlags.join(', ')}.`
      : 'No major integration hotspots detected for this request.',
  };
}

function analyzeRepositoryImpact({ repositoryAnalysis, message }) {
  const hotspots = inferHotspots(repositoryAnalysis);
  const moduleCandidates = pickModuleCandidates(repositoryAnalysis, message);
  const testSelectionCandidates = pickTestCandidates(repositoryAnalysis, moduleCandidates);
  const integrationRiskSummary = buildIntegrationRiskSummary(repositoryAnalysis, moduleCandidates, hotspots);
  return {
    version: 1,
    message_preview: String(message || '').slice(0, 160),
    impact_map: {
      entry_points: repositoryAnalysis?.repository_map?.entry_points || [],
      hotspot_files: hotspots,
      candidate_count: moduleCandidates.length,
      likely_affected_modules: moduleCandidates.map(item => item.path),
    },
    module_change_candidates: moduleCandidates,
    test_selection_candidates: testSelectionCandidates,
    integration_risk_summary: integrationRiskSummary,
    generated_at: new Date().toISOString(),
  };
}

module.exports = {
  analyzeRepositoryImpact,
};

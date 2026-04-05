const fs = require('fs');
const path = require('path');

function getLearningPath(cwd) {
  const dir = path.join(cwd, '.logs', 'fusion-runtime');
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, 'execution-learning-memory.json');
}

function loadExecutionLearningMemory(cwd) {
  const filePath = getLearningPath(cwd);
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    return Array.isArray(parsed.entries) ? parsed : { entries: [] };
  } catch {
    return { entries: [] };
  }
}

function saveExecutionLearningMemory(cwd, payload) {
  const filePath = getLearningPath(cwd);
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), 'utf8');
  return filePath;
}

function inferArchetype(message) {
  const text = String(message || '').toLowerCase();
  if (text.includes('analise') || text.includes('resuma')) return 'analysis';
  if (text.includes('liste') || text.includes('arquivos') || text.includes('leia')) return 'inspection';
  if (text.includes('escreva') || text.includes('crie o arquivo')) return 'mutation';
  return 'general';
}

function buildLearningEntry(entry = {}) {
  const confidence = Math.max(0, Math.min(1, Number(entry.confidence ?? 0.5)));
  const successCount = Math.max(0, Number(entry.success_count ?? (entry.outcome === 'success' ? 1 : 0)));
  const failureCount = Math.max(0, Number(entry.failure_count ?? (entry.outcome === 'failure' ? 1 : 0)));
  const avoidanceCount = Math.max(0, Number(entry.avoidance_count ?? (entry.outcome === 'failure_avoidance' ? 1 : 0)));
  const rankingScore = Number(
    entry.ranking_score
      ?? (confidence * 2 + successCount * 1.5 + avoidanceCount * 1.2 - failureCount * 1.5),
  );
  return {
    entry_id: String(entry.entry_id || `${entry.task_id || 'task'}:${entry.run_id || 'run'}:${Date.now()}`),
    task_id: String(entry.task_id || ''),
    run_id: String(entry.run_id || ''),
    session_id: String(entry.session_id || ''),
    archetype: String(entry.archetype || inferArchetype(entry.message || 'general')),
    strategy_type: String(entry.strategy_type || 'execution_pattern'),
    outcome: String(entry.outcome || 'neutral'),
    lesson: String(entry.lesson || '').trim(),
    confidence,
    tool_family: String(entry.tool_family || 'unknown'),
    trigger: String(entry.trigger || ''),
    transcript_ref: entry.transcript_ref || null,
    metadata: entry.metadata || {},
    success_count: successCount,
    failure_count: failureCount,
    avoidance_count: avoidanceCount,
    ranking_score: Number.isFinite(rankingScore) ? rankingScore : 0,
    updated_at: entry.updated_at || new Date().toISOString(),
  };
}

function recordLearningEntry(cwd, entry = {}) {
  const store = loadExecutionLearningMemory(cwd);
  const normalized = buildLearningEntry(entry);
  const filtered = store.entries.filter(existing => existing.entry_id !== normalized.entry_id);
  filtered.unshift(normalized);
  store.entries = filtered.slice(0, 200);
  saveExecutionLearningMemory(cwd, store);
  return normalized;
}

function recordStrategyOutcome(cwd, entry = {}) {
  const store = loadExecutionLearningMemory(cwd);
  const taskType = inferArchetype(entry.message || entry.lesson || '');
  const existing = store.entries.find(item =>
    String(item.strategy_type || '') === String(entry.strategy_type || 'execution_pattern')
    && String(item.archetype || '') === String(entry.archetype || taskType)
    && String(item.tool_family || '') === String(entry.tool_family || 'unknown')
    && String(item.lesson || '').trim() === String(entry.lesson || '').trim(),
  );

  const successCount = Math.max(0, Number(existing?.success_count || 0)) + (entry.outcome === 'success' ? 1 : 0);
  const failureCount = Math.max(0, Number(existing?.failure_count || 0)) + (entry.outcome === 'failure' ? 1 : 0);
  const avoidanceCount = Math.max(0, Number(existing?.avoidance_count || 0)) + (entry.outcome === 'failure_avoidance' ? 1 : 0);
  const confidence = Math.max(
    0,
    Math.min(
      1,
      Number(entry.confidence ?? existing?.confidence ?? 0.5)
      + (entry.outcome === 'success' ? 0.08 : 0)
      + (entry.outcome === 'failure_avoidance' ? 0.04 : 0)
      - (entry.outcome === 'failure' ? 0.1 : 0),
    ),
  );
  const rankingScore = confidence * 2 + successCount * 1.5 + avoidanceCount * 1.2 - failureCount * 1.5;
  const normalized = buildLearningEntry({
    ...existing,
    ...entry,
    archetype: entry.archetype || existing?.archetype || taskType,
    confidence,
    success_count: successCount,
    failure_count: failureCount,
    avoidance_count: avoidanceCount,
    ranking_score: rankingScore,
    entry_id: existing?.entry_id || entry.entry_id,
  });
  const filtered = store.entries.filter(item => item.entry_id !== normalized.entry_id);
  filtered.unshift(normalized);
  store.entries = filtered.slice(0, 200);
  saveExecutionLearningMemory(cwd, store);
  return normalized;
}

function suggestRankedStrategies(cwd, { message = '', toolFamily = '', limit = 3 } = {}) {
  return findLearningMatches(cwd, { message, toolFamily, limit })
    .map(entry => ({
      entry_id: entry.entry_id,
      strategy_type: entry.strategy_type,
      archetype: entry.archetype,
      lesson: entry.lesson,
      confidence: Number(entry.confidence || 0),
      ranking_score: Number(entry.ranking_score || entry.score || 0),
      task_similarity: Number(entry.score || 0),
      provenance: {
        task_id: entry.task_id,
        run_id: entry.run_id,
        trigger: entry.trigger,
      },
      metadata: entry.metadata || {},
    }))
    .sort((a, b) => b.ranking_score - a.ranking_score)
    .slice(0, limit);
}

function findLearningMatches(cwd, { message = '', toolFamily = '', limit = 5 } = {}) {
  const store = loadExecutionLearningMemory(cwd);
  const archetype = inferArchetype(message);
  const tokens = new Set(String(message || '').toLowerCase().split(/\W+/).filter(Boolean));
  const ranked = store.entries
    .map(entry => {
      let score = 0;
      if (entry.archetype === archetype) score += 3;
      if (toolFamily && entry.tool_family === toolFamily) score += 2;
      const lessonTokens = String(entry.lesson || '').toLowerCase().split(/\W+/).filter(Boolean);
      score += lessonTokens.filter(token => tokens.has(token)).length;
      if (entry.outcome === 'success') score += 1;
      if (entry.outcome === 'failure_avoidance') score += 2;
      score += Number(entry.confidence || 0);
      score += Number(entry.ranking_score || 0);
      return { ...entry, score };
    })
    .filter(entry => entry.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
  return ranked;
}

module.exports = {
  buildLearningEntry,
  findLearningMatches,
  getLearningPath,
  inferArchetype,
  loadExecutionLearningMemory,
  recordLearningEntry,
  recordStrategyOutcome,
  saveExecutionLearningMemory,
  suggestRankedStrategies,
};

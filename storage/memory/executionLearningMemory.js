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
  saveExecutionLearningMemory,
};

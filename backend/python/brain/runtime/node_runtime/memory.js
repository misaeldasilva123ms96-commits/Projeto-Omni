function getUserMemory(memoryContext) {
  const user = memoryContext?.user;
  if (!user || typeof user !== 'object') {
    return { nome: '', preferencias: [] };
  }

  return {
    nome: typeof user.nome === 'string' ? user.nome.trim() : '',
    preferencias: Array.isArray(user.preferencias)
      ? user.preferencias.map(item => String(item).trim()).filter(Boolean)
      : [],
  };
}

function getRecentUserMessages(history) {
  if (!Array.isArray(history)) {
    return [];
  }

  return history
    .filter(item => item?.role === 'user' && typeof item?.content === 'string')
    .map(item => item.content.trim())
    .filter(Boolean)
    .slice(-6);
}

function buildContextSummary(history, summary, session) {
  if (summary && String(summary).trim()) {
    return String(summary).trim();
  }

  const sessionSummary = session?.summary;
  if (typeof sessionSummary === 'string' && sessionSummary.trim()) {
    return sessionSummary.trim();
  }

  const recent = getRecentUserMessages(history);
  if (recent.length === 0) {
    return 'Sem contexto anterior relevante.';
  }

  return recent.join(' | ');
}

function hasPreference(preferences, keyword) {
  return preferences.some(item => String(item).toLowerCase().includes(keyword));
}

function buildMemorySignal(thought, executionPlan) {
  return {
    intent: thought.intent,
    usedName: Boolean(thought.userName),
    usedPreferences: thought.preferences.length > 0,
    executionPlan: executionPlan || [],
    delegates: thought.delegates,
    contextSummary: thought.contextSummary,
    memoryHint: {
      userName: thought.userName,
      preferences: thought.preferences,
      recentHistory: thought.recentHistory,
    },
  };
}

module.exports = {
  getUserMemory,
  getRecentUserMessages,
  buildContextSummary,
  hasPreference,
  buildMemorySignal,
};

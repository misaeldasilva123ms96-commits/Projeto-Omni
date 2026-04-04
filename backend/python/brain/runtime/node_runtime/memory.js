function getUserMemory(memoryContext) {
  const user = memoryContext?.user;
  if (!user || typeof user !== 'object') {
    return {
      id: '',
      nome: '',
      trabalho: '',
      preferencias: [],
      responseStyle: 'balanced',
      depthPreference: 'medium',
      recurringTopics: [],
      goals: [],
    };
  }

  return {
    id: typeof user.id === 'string' ? user.id.trim() : '',
    nome: typeof user.nome === 'string' ? user.nome.trim() : '',
    trabalho: typeof user.trabalho === 'string' ? user.trabalho.trim() : '',
    preferencias: Array.isArray(user.preferencias)
      ? user.preferencias.map(item => String(item).trim()).filter(Boolean)
      : [],
    responseStyle: typeof user.response_style === 'string' ? user.response_style.trim() : 'balanced',
    depthPreference: typeof user.depth_preference === 'string' ? user.depth_preference.trim() : 'medium',
    recurringTopics: Array.isArray(user.recurring_topics)
      ? user.recurring_topics.map(item => String(item).trim()).filter(Boolean)
      : [],
    goals: Array.isArray(user.goals)
      ? user.goals.map(item => String(item).trim()).filter(Boolean)
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
    usedWork: Boolean(thought.work),
    usedPreferences: thought.preferences.length > 0,
    usedGoals: thought.goals.length > 0,
    executionPlan: executionPlan || [],
    delegates: thought.delegates,
    contextSummary: thought.contextSummary,
    memoryHint: {
      userId: thought.userId,
      userName: thought.userName,
      work: thought.work,
      preferences: thought.preferences,
      responseStyle: thought.responseStyle,
      depthPreference: thought.depthPreference,
      recurringTopics: thought.recurringTopics,
      goals: thought.goals,
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

function review(thought, decision, actionResult) {
  const issues = [];

  if (!actionResult || typeof actionResult !== 'object') {
    issues.push('sem payload de execucao');
  }

  if (thought.contextSummary === 'Sem contexto anterior relevante.' && thought.recentHistory.length === 0) {
    issues.push('baixo contexto historico');
  }

  if (decision.strategy === 'contextual_conversation' && thought.intent !== 'conversa') {
    issues.push('estrategia generica para intent especifica');
  }

  return {
    approved: true,
    issues,
    qualityScore: issues.length === 0 ? 0.9 : 0.76,
  };
}

module.exports = {
  review,
};

function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function containsMetaResponse(text) {
  const normalized = normalizeText(text);
  return [
    'o mais util e',
    'eu responderia assim',
    'tratar este ponto',
    'vale mostrar por que isso importa',
  ].some(marker => normalized.includes(marker));
}

function review(thought, decision, actionResult) {
  const issues = [];
  let qualityScore = 0.9;

  if (!actionResult || typeof actionResult !== 'object') {
    issues.push('sem payload de execucao');
    qualityScore = 0.3;
  }

  if (thought.contextSummary === 'Sem contexto anterior relevante.' && thought.recentHistory.length === 0) {
    issues.push('baixo contexto historico');
    qualityScore -= 0.04;
  }

  if (decision.strategy === 'contextual_conversation' && thought.intent !== 'conversa') {
    issues.push('estrategia generica para intent especifica');
    qualityScore -= 0.08;
  }

  if (containsMetaResponse(actionResult?.response || '') && (thought.highComplexity || thought.requiresLlm)) {
    issues.push('meta_resposta_em_tarefa_complexa');
    qualityScore = Math.min(qualityScore, 0.3);
  }

  if ((thought.taskCategory === 'theory_of_mind' || thought.taskCategory === 'logic') && !normalizeText(actionResult?.response || '').includes('mesa') && normalizeText(thought.message).includes('mesa')) {
    issues.push('falha_logica');
    qualityScore = Math.min(qualityScore, 0.38);
  }

  return {
    approved: !issues.includes('meta_resposta_em_tarefa_complexa'),
    issues,
    qualityScore: Math.max(0.2, Number(qualityScore.toFixed(2))),
  };
}

module.exports = {
  review,
};

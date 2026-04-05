function shouldReflect({ complexity = 'simple', stepResults = [], policyDecision = null, runtimeConfig = {} }) {
  const enabled = runtimeConfig.reflectionEnabled !== false;
  if (!enabled) return false;
  const failures = stepResults.filter(result => !result.ok);
  if (policyDecision?.decision && policyDecision.decision !== 'allow') return true;
  if (failures.length > 0) return true;
  return complexity === 'complex' && stepResults.length >= 2;
}

function buildReflectionSummary({ message, stepResults = [], learningMatches = [], policyDecision = null, hierarchy = null }) {
  const failed = stepResults.filter(result => !result.ok);
  const successful = stepResults.filter(result => result.ok);
  const hierarchySummary = hierarchy?.subgoals?.length
    ? `Hierarquia executada com ${hierarchy.subgoals.length} subobjetivos.`
    : '';
  const failureSummary = failed.length
    ? `Falhas observadas: ${failed.map(item => item.selected_tool || 'tool').join(', ')}.`
    : 'Execucao concluida sem falhas criticas.';
  const learningHint = learningMatches[0]?.lesson ? `Licao reaproveitada: ${learningMatches[0].lesson}` : '';
  const policyHint = policyDecision?.reason_code ? `Politica aplicada: ${policyDecision.reason_code}.` : '';
  const nextPreference = failed.length
    ? 'Preferir revisao de plano e evitar repetir a mesma estrategia sem nova evidencia.'
    : 'Manter a estrategia bem-sucedida para tarefas semelhantes.';
  return {
    invoked: true,
    reason_code: failed.length ? 'execution_quality_review' : 'post_run_complexity_review',
    summary: [hierarchySummary, failureSummary, learningHint, policyHint, nextPreference]
      .filter(Boolean)
      .join(' '),
    update_learning: failed.length > 0 || successful.length > 1,
    message_preview: String(message || '').slice(0, 120),
  };
}

module.exports = {
  buildReflectionSummary,
  shouldReflect,
};

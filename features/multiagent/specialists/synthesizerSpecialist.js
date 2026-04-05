function synthesizeStepNarrative(stepResults = []) {
  return stepResults
    .map(result => {
      const tool = result.selected_tool || result.action?.selected_tool || 'unknown_tool';
      if (result.ok) {
        return `Etapa ${tool}: concluída.`;
      }
      const message = result.error_payload?.message || result.error?.message || 'falha sem detalhe';
      return `Etapa ${tool}: falhou porque ${message}.`;
    })
    .join(' ');
}

function synthesizeGroundedResponse({ intent, directMemoryResponse, stepResults, fallbackResponse = '' }) {
  if (directMemoryResponse) {
    return directMemoryResponse;
  }

  const readResults = stepResults.filter(result => result.ok && result.summary && result.selected_tool === 'read_file');
  if (readResults.length > 0) {
    return readResults[readResults.length - 1].summary;
  }

  const successful = stepResults.filter(result => result.ok && result.summary);
  const failed = stepResults.find(result => !result.ok);
  if (successful.length === 0 && failed) {
    return `Não consegui concluir a tarefa. ${synthesizeStepNarrative(stepResults)}`.trim();
  }

  if (successful.length === 0) {
    return fallbackResponse || 'Não encontrei execução suficiente para responder com segurança.';
  }

  const body = successful.map(result => result.summary).join('\n\n').trim();
  if (!failed) {
    return body;
  }
  return `${body}\n\n${synthesizeStepNarrative(stepResults)}`.trim();
}

module.exports = {
  synthesizeGroundedResponse,
  synthesizeStepNarrative,
};

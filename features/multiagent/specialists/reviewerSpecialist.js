function synthesizeFinalAnswer({ intent, directMemoryResponse, stepResults }) {
  if (directMemoryResponse) {
    return directMemoryResponse;
  }

  if (intent === 'greeting') {
    return 'Olá! Como posso te ajudar hoje?';
  }

  const successful = stepResults.filter(item => item.ok && item.summary);
  const failure = stepResults.find(item => !item.ok);

  if (successful.length === 0 && failure) {
    return `Não consegui concluir a execução porque ${failure.error_payload?.message || failure.error?.message || 'ocorreu uma falha na ferramenta'}.`;
  }

  if (successful.length === 0) {
    return 'Não encontrei uma ação executável para esse pedido ainda.';
  }

  const body = successful.map(item => item.summary).filter(Boolean).join('\n\n').trim();
  if (!failure) {
    return body;
  }

  return `${body}\n\nNão concluí os passos restantes porque ${failure.error_payload?.message || failure.error?.message || 'houve uma falha de execução'}.`.trim();
}

module.exports = {
  synthesizeFinalAnswer,
};

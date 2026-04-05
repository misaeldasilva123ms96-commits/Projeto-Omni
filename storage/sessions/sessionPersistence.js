function buildSessionSnapshot({ session, summary, delegates, provider, contract }) {
  return {
    session_id: session?.session_id || 'ephemeral-session',
    summary: summary || '',
    delegates: Array.isArray(delegates) ? delegates : [],
    provider: provider?.name || 'local-heuristic',
    contract_version: contract?.version || '1.0.0',
    runtime_mode: session?.runtime_mode || 'auto',
  };
}

module.exports = {
  buildSessionSnapshot,
};

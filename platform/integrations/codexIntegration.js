function getCodexIntegrationStatus() {
  const hasCodexKey = Boolean(process.env.CODEX_API_KEY || process.env.OPENAI_API_KEY);
  const hasAccountId = Boolean(process.env.CHATGPT_ACCOUNT_ID);

  return {
    available: hasCodexKey,
    source: 'openclaude-main.zip',
    transport: hasAccountId ? 'codex-responses' : 'openai-compatible',
    capabilities: [
      'provider bootstrap',
      'coding-agent compatible routing',
      'profile-driven model selection',
    ],
  };
}

module.exports = {
  getCodexIntegrationStatus,
};

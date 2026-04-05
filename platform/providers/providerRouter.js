function envValue(name) {
  const value = process.env[name];
  return typeof value === 'string' ? value.trim() : '';
}

function hasConfig(name) {
  return Boolean(envValue(name));
}

function getAvailableProviders() {
  const providers = [];

  if (hasConfig('OPENAI_API_KEY')) {
    providers.push({
      name: 'openai',
      source: 'openclaude-main.zip',
      model: envValue('OPENAI_MODEL') || 'gpt-4.1-mini',
      priority: 1,
      kind: 'remote',
    });
  }

  if (hasConfig('ANTHROPIC_API_KEY')) {
    providers.push({
      name: 'anthropic',
      source: 'openclaude-main.zip',
      model: envValue('ANTHROPIC_MODEL') || 'claude-3-5-sonnet-latest',
      priority: 2,
      kind: 'remote',
    });
  }

  if (hasConfig('OLLAMA_URL')) {
    providers.push({
      name: 'ollama',
      source: 'openclaude-main.zip',
      model: envValue('OLLAMA_MODEL') || 'llama3:8b',
      priority: 3,
      kind: 'local',
      baseUrl: envValue('OLLAMA_URL'),
    });
  }

  providers.push({
    name: 'local-heuristic',
    source: 'project',
    model: 'native-heuristic',
    priority: 99,
    kind: 'embedded',
  });

  return providers;
}

function chooseProvider({ complexity = 'simple', preferred = '' } = {}) {
  const providers = getAvailableProviders();
  const normalizedPreferred = String(preferred || '').trim().toLowerCase();

  if (normalizedPreferred) {
    const exact = providers.find(provider => provider.name === normalizedPreferred);
    if (exact) {
      return exact;
    }
  }

  if (complexity === 'complex') {
    return providers.find(provider => provider.kind !== 'embedded') || providers[providers.length - 1];
  }

  return providers[0];
}

module.exports = {
  chooseProvider,
  getAvailableProviders,
};

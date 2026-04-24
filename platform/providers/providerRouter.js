function envValue(name) {
  const value = process.env[name];
  return typeof value === 'string' ? value.trim() : '';
}

function hasConfig(name) {
  return Boolean(envValue(name));
}

/**
 * Comma-separated logical ids from Python (validated keys only). Used for routing order hints.
 */
function parseOmniAvailableProviders() {
  const raw = envValue('OMINI_AVAILABLE_PROVIDERS');
  if (!raw) {
    return null;
  }
  return raw.split(/[,]+/).map(part => part.trim().toLowerCase()).filter(Boolean);
}

function getAvailableProviders() {
  const remote = [];

  if (hasConfig('OPENAI_API_KEY')) {
    remote.push({
      name: 'openai',
      source: 'openclaude-main.zip',
      model: envValue('OPENAI_MODEL') || 'gpt-4.1-mini',
      priority: 1,
      kind: 'remote',
    });
  }

  if (hasConfig('ANTHROPIC_API_KEY')) {
    remote.push({
      name: 'anthropic',
      source: 'openclaude-main.zip',
      model: envValue('ANTHROPIC_MODEL') || 'claude-3-5-sonnet-latest',
      priority: 2,
      kind: 'remote',
    });
  }

  if (hasConfig('GROQ_API_KEY')) {
    remote.push({
      name: 'groq',
      source: 'project',
      model: envValue('GROQ_MODEL') || 'llama-3.3-70b-versatile',
      priority: 3,
      kind: 'remote',
    });
  }

  if (hasConfig('GEMINI_API_KEY')) {
    remote.push({
      name: 'gemini',
      source: 'project',
      model: envValue('GEMINI_MODEL') || 'gemini-2.0-flash',
      priority: 4,
      kind: 'remote',
    });
  }

  if (hasConfig('DEEPSEEK_API_KEY')) {
    remote.push({
      name: 'deepseek',
      source: 'project',
      model: envValue('DEEPSEEK_MODEL') || 'deepseek-chat',
      priority: 5,
      kind: 'remote',
    });
  }

  if (hasConfig('OLLAMA_URL')) {
    remote.push({
      name: 'ollama',
      source: 'openclaude-main.zip',
      model: envValue('OLLAMA_MODEL') || 'llama3:8b',
      priority: 6,
      kind: 'local',
      baseUrl: envValue('OLLAMA_URL'),
    });
  }

  const order = parseOmniAvailableProviders();
  if (order && order.length) {
    const rank = new Map(order.map((name, index) => [name, index]));
    remote.sort((a, b) => {
      const ra = rank.has(a.name) ? rank.get(a.name) : 999;
      const rb = rank.has(b.name) ? rank.get(b.name) : 999;
      if (ra !== rb) {
        return ra - rb;
      }
      return (a.priority || 99) - (b.priority || 99);
    });
  } else {
    remote.sort((a, b) => (a.priority || 99) - (b.priority || 99));
  }

  remote.push({
    name: 'local-heuristic',
    source: 'project',
    model: 'native-heuristic',
    priority: 99,
    kind: 'embedded',
  });

  return remote;
}

function buildProviderDiagnostics({
  selectedProviderName = '',
  actualProviderName = '',
  attemptedProviderName = '',
  succeededProviderName = '',
  failureClass = '',
  failureReason = '',
  latencyMs = null,
} = {}) {
  const selected = String(selectedProviderName || '').trim().toLowerCase();
  const actual = String(actualProviderName || '').trim().toLowerCase();
  const attempted = String(attemptedProviderName || actual || '').trim().toLowerCase();
  const succeeded = String(succeededProviderName || (failureClass ? '' : actual) || '').trim().toLowerCase();
  const failureKind = String(failureClass || '').trim().toLowerCase();
  const failureDetail = String(failureReason || '').trim();
  const providers = getAvailableProviders();

  return providers.map(provider => {
    const attemptedHere = provider.name === attempted;
    const succeededHere = provider.name === succeeded && !failureKind;
    const failedHere = attemptedHere && Boolean(failureKind);
    return {
      provider: provider.name,
      configured: provider.kind === 'embedded' ? true : provider.kind === 'local' ? Boolean(provider.baseUrl) : true,
      available: true,
      selected: provider.name === selected,
      attempted: attemptedHere,
      succeeded: succeededHere,
      failed: failedHere,
      failure_class: failedHere ? failureKind : null,
      failure_reason: failedHere ? failureDetail || null : null,
      latency_ms: attemptedHere && latencyMs != null ? Number(latencyMs) : null,
    };
  });
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
  buildProviderDiagnostics,
  chooseProvider,
  getAvailableProviders,
};

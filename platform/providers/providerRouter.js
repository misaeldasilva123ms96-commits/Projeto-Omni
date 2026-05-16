function envValue(name) {
  const value = process.env[name];
  return typeof value === 'string' ? value.trim() : '';
}

function hasConfig(name) {
  return Boolean(envValue(name));
}

const PROVIDER_DEFINITIONS = Object.freeze([
  Object.freeze({
    name: 'groq',
    source: 'project',
    envVar: 'GROQ_API_KEY',
    modelEnvVar: 'GROQ_MODEL',
    defaultModel: 'llama-3.3-70b-versatile',
    priority: 3,
    kind: 'remote',
    registered: true,
    adapter_implemented: true,
    enabled_by_default: true,
    execution_status: 'credential_gated',
  }),
  Object.freeze({
    name: 'openrouter',
    source: 'project',
    envVar: 'OPENROUTER_API_KEY',
    modelEnvVar: 'OPENROUTER_MODEL',
    defaultModel: 'openrouter-default',
    priority: 20,
    kind: 'remote',
    registered: true,
    adapter_implemented: false,
    enabled_by_default: false,
    execution_status: 'unsupported',
  }),
  Object.freeze({
    name: 'openai',
    source: 'openclaude-main.zip',
    envVar: 'OPENAI_API_KEY',
    modelEnvVar: 'OPENAI_MODEL',
    defaultModel: 'gpt-4.1-mini',
    priority: 30,
    kind: 'remote',
    registered: true,
    adapter_implemented: false,
    enabled_by_default: false,
    execution_status: 'unsupported',
  }),
  Object.freeze({
    name: 'anthropic',
    source: 'openclaude-main.zip',
    envVar: 'ANTHROPIC_API_KEY',
    modelEnvVar: 'ANTHROPIC_MODEL',
    defaultModel: 'claude-3-5-sonnet-latest',
    priority: 40,
    kind: 'remote',
    registered: true,
    adapter_implemented: false,
    enabled_by_default: false,
    execution_status: 'unsupported',
  }),
  Object.freeze({
    name: 'gemini',
    source: 'project',
    envVar: 'GEMINI_API_KEY',
    modelEnvVar: 'GEMINI_MODEL',
    defaultModel: 'gemini-2.0-flash',
    priority: 50,
    kind: 'remote',
    registered: true,
    adapter_implemented: false,
    enabled_by_default: false,
    execution_status: 'unsupported',
  }),
  Object.freeze({
    name: 'deepseek',
    source: 'project',
    envVar: 'DEEPSEEK_API_KEY',
    modelEnvVar: 'DEEPSEEK_MODEL',
    defaultModel: 'deepseek-chat',
    priority: 60,
    kind: 'remote',
    registered: true,
    adapter_implemented: false,
    enabled_by_default: false,
    execution_status: 'unsupported',
  }),
  Object.freeze({
    name: 'ollama',
    source: 'openclaude-main.zip',
    envVar: 'OLLAMA_URL',
    modelEnvVar: 'OLLAMA_MODEL',
    defaultModel: 'llama3:8b',
    priority: 70,
    kind: 'local',
    registered: true,
    adapter_implemented: false,
    enabled_by_default: false,
    execution_status: 'local_config_gated',
  }),
  Object.freeze({
    name: 'lmstudio',
    source: 'project',
    envVar: 'LMSTUDIO_URL',
    modelEnvVar: 'LMSTUDIO_MODEL',
    defaultModel: 'lmstudio-local',
    priority: 80,
    kind: 'local',
    registered: true,
    adapter_implemented: false,
    enabled_by_default: false,
    execution_status: 'local_config_gated',
  }),
]);

const LOCAL_HEURISTIC_PROVIDER = Object.freeze({
  name: 'local-heuristic',
  source: 'project',
  model: 'native-heuristic',
  priority: 99,
  kind: 'embedded',
  registered: true,
  configured: true,
  key_present: false,
  model_configured: true,
  adapter_implemented: true,
  enabled_by_default: true,
  execution_status: 'active',
  executable: true,
  available: true,
});

function materializeProvider(definition) {
  const configured = hasConfig(definition.envVar);
  const model = envValue(definition.modelEnvVar) || definition.defaultModel;
  const executable = Boolean(definition.adapter_implemented && configured);
  const provider = {
    name: definition.name,
    source: definition.source,
    model,
    priority: definition.priority,
    kind: definition.kind,
    registered: Boolean(definition.registered),
    configured,
    key_present: definition.kind === 'remote' ? configured : false,
    model_configured: Boolean(model),
    adapter_implemented: Boolean(definition.adapter_implemented),
    enabled_by_default: Boolean(definition.enabled_by_default),
    execution_status: definition.adapter_implemented
      ? (configured ? 'active' : 'credential_gated')
      : definition.execution_status,
    executable,
    available: executable,
  };
  return provider;
}

function getProviderRegistry({ includeEmbeddedLocal = false } = {}) {
  const rows = PROVIDER_DEFINITIONS.map(materializeProvider);
  if (includeEmbeddedLocal) {
    rows.push({ ...LOCAL_HEURISTIC_PROVIDER });
  }
  return rows;
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
  const remote = getProviderRegistry()
    .filter(provider => provider.executable);

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

  remote.push({ ...LOCAL_HEURISTIC_PROVIDER });

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
  const providers = getProviderRegistry({ includeEmbeddedLocal: true });

  return providers.map(provider => {
    const attemptedHere = provider.name === attempted;
    const succeededHere = provider.name === succeeded && !failureKind;
    const failedHere = attemptedHere && Boolean(failureKind);
    return {
      provider: provider.name,
      registered: Boolean(provider.registered),
      configured: Boolean(provider.configured),
      key_present: Boolean(provider.key_present),
      model_configured: Boolean(provider.model_configured),
      adapter_implemented: Boolean(provider.adapter_implemented),
      enabled_by_default: Boolean(provider.enabled_by_default),
      execution_status: String(provider.execution_status || 'unsupported'),
      executable: Boolean(provider.executable),
      available: Boolean(provider.available),
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
  getProviderRegistry,
};

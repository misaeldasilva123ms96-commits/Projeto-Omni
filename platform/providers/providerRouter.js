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
    defaultModel: 'openai/gpt-4o-mini',
    priority: 20,
    kind: 'remote',
    registered: true,
    adapter_implemented: true,
    enabled_by_default: false,
    execution_status: 'credential_gated',
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

const DEFAULT_FALLBACK_CHAIN = Object.freeze(['groq', 'openrouter', 'local-heuristic']);

const FALLBACK_REASONS = Object.freeze({
  REQUESTED_PROVIDER_UNSUPPORTED: 'requested_provider_unsupported',
  REQUESTED_PROVIDER_UNAVAILABLE: 'requested_provider_unavailable',
  NO_REMOTE_PROVIDER_AVAILABLE: 'no_remote_provider_available',
});

function normalizeProviderName(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return normalized || null;
}

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

function sortProvidersByPolicy(providers) {
  const sorted = providers.slice();
  const order = parseOmniAvailableProviders();
  if (order && order.length) {
    const rank = new Map(order.map((name, index) => [name, index]));
    sorted.sort((a, b) => {
      if ((a.priority || 99) !== (b.priority || 99)) {
        return (a.priority || 99) - (b.priority || 99);
      }
      const ra = rank.has(a.name) ? rank.get(a.name) : 999;
      const rb = rank.has(b.name) ? rank.get(b.name) : 999;
      if (ra !== rb) {
        return ra - rb;
      }
      return (a.priority || 99) - (b.priority || 99);
    });
  } else {
    sorted.sort((a, b) => (a.priority || 99) - (b.priority || 99));
  }
  return sorted;
}

function getAvailableProviders() {
  const remote = sortProvidersByPolicy(
    getProviderRegistry().filter(provider => provider.executable),
  );

  remote.push({ ...LOCAL_HEURISTIC_PROVIDER });

  return remote;
}

function fallbackReasonForRequestedProvider(provider) {
  if (!provider) {
    return FALLBACK_REASONS.REQUESTED_PROVIDER_UNAVAILABLE;
  }
  if (!provider.adapter_implemented || provider.execution_status === 'unsupported') {
    return FALLBACK_REASONS.REQUESTED_PROVIDER_UNSUPPORTED;
  }
  return FALLBACK_REASONS.REQUESTED_PROVIDER_UNAVAILABLE;
}

function selectFallbackProvider(providersByName) {
  for (const name of DEFAULT_FALLBACK_CHAIN) {
    const candidate = providersByName.get(name);
    if (!candidate || !candidate.executable) {
      continue;
    }
    if (candidate.kind === 'embedded') {
      return {
        executionProvider: null,
        localFallbackProvider: { ...candidate },
        fallbackProvider: { ...candidate },
      };
    }
    return {
      executionProvider: { ...candidate },
      localFallbackProvider: null,
      fallbackProvider: { ...candidate },
    };
  }

  return {
    executionProvider: null,
    localFallbackProvider: null,
    fallbackProvider: null,
  };
}

function buildRouteOutcome({
  requestedProviderName = null,
  selectedProviderName = null,
  executionProvider = null,
  localFallbackProvider = null,
  fallbackProvider = null,
  fallbackTriggered = false,
  fallbackReason = '',
  noRemoteProviderAvailable = false,
  noProviderAvailable = false,
} = {}) {
  return {
    requestedProviderName,
    selectedProviderName,
    executionProvider,
    executionProviderName: executionProvider?.name || null,
    localFallbackProvider,
    localFallbackProviderName: localFallbackProvider?.name || null,
    fallbackProvider,
    fallbackProviderName: fallbackProvider?.name || null,
    fallbackTriggered: Boolean(fallbackTriggered),
    fallbackReason: String(fallbackReason || ''),
    noRemoteProviderAvailable: Boolean(noRemoteProviderAvailable),
    noProviderAvailable: Boolean(noProviderAvailable),
  };
}

function resolveProviderRoute({ complexity = 'simple', preferred = '' } = {}) {
  const registry = getProviderRegistry({ includeEmbeddedLocal: true });
  const providersByName = new Map(registry.map(provider => [provider.name, provider]));
  const remoteExecutable = sortProvidersByPolicy(
    registry.filter(provider => provider.kind !== 'embedded' && provider.executable),
  );
  const noRemoteProviderAvailable = remoteExecutable.length === 0;
  const requestedProviderName = normalizeProviderName(preferred);
  const requestedProvider = requestedProviderName ? providersByName.get(requestedProviderName) : null;

  if (requestedProvider?.executable) {
    if (requestedProvider.kind === 'embedded') {
      return buildRouteOutcome({
        requestedProviderName,
        selectedProviderName: requestedProvider.name,
        localFallbackProvider: { ...requestedProvider },
        noRemoteProviderAvailable,
      });
    }
    return buildRouteOutcome({
      requestedProviderName,
      selectedProviderName: requestedProvider.name,
      executionProvider: { ...requestedProvider },
      noRemoteProviderAvailable,
    });
  }

  if (requestedProviderName) {
    const fallback = selectFallbackProvider(providersByName);
    const selected = fallback.executionProvider || fallback.localFallbackProvider;
    return buildRouteOutcome({
      requestedProviderName,
      selectedProviderName: selected?.name || null,
      executionProvider: fallback.executionProvider,
      localFallbackProvider: fallback.localFallbackProvider,
      fallbackProvider: fallback.fallbackProvider,
      fallbackTriggered: true,
      fallbackReason: fallbackReasonForRequestedProvider(requestedProvider),
      noRemoteProviderAvailable,
      noProviderAvailable: !selected,
    });
  }

  const selectedProvider = complexity === 'complex'
    ? remoteExecutable[0]
    : remoteExecutable[0];
  if (selectedProvider) {
    return buildRouteOutcome({
      selectedProviderName: selectedProvider.name,
      executionProvider: { ...selectedProvider },
      noRemoteProviderAvailable,
    });
  }

  const fallback = selectFallbackProvider(providersByName);
  const selected = fallback.executionProvider || fallback.localFallbackProvider;
  return buildRouteOutcome({
    selectedProviderName: selected?.name || null,
    executionProvider: fallback.executionProvider,
    localFallbackProvider: fallback.localFallbackProvider,
    fallbackProvider: fallback.fallbackProvider,
    fallbackTriggered: true,
    fallbackReason: FALLBACK_REASONS.NO_REMOTE_PROVIDER_AVAILABLE,
    noRemoteProviderAvailable: true,
    noProviderAvailable: !selected,
  });
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
  DEFAULT_FALLBACK_CHAIN,
  FALLBACK_REASONS,
  buildProviderDiagnostics,
  chooseProvider,
  getAvailableProviders,
  getProviderRegistry,
  resolveProviderRoute,
};

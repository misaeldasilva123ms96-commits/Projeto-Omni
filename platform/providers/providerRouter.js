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
    defaultModel: 'gpt-4o-mini',
    priority: 30,
    kind: 'remote',
    registered: true,
    adapter_implemented: true,
    enabled_by_default: false,
    execution_status: 'credential_gated',
  }),
  Object.freeze({
    name: 'anthropic',
    source: 'openclaude-main.zip',
    envVar: 'ANTHROPIC_API_KEY',
    modelEnvVar: 'ANTHROPIC_MODEL',
    defaultModel: 'claude-haiku-4-5-20251001',
    priority: 40,
    kind: 'remote',
    registered: true,
    adapter_implemented: true,
    enabled_by_default: false,
    execution_status: 'credential_gated',
  }),
  Object.freeze({
    name: 'gemini',
    source: 'project',
    envVar: 'GEMINI_API_KEY',
    modelEnvVar: 'GEMINI_MODEL',
    defaultModel: 'gemini-2.5-flash',
    priority: 50,
    kind: 'remote',
    registered: true,
    adapter_implemented: true,
    enabled_by_default: false,
    execution_status: 'credential_gated',
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
    defaultModel: 'llama3',
    priority: 70,
    kind: 'local',
    registered: true,
    adapter_implemented: true,
    enabled_by_default: false,
    execution_status: 'local_config_gated',
  }),
  Object.freeze({
    name: 'lmstudio',
    source: 'project',
    envVar: 'LMSTUDIO_URL',
    modelEnvVar: 'LMSTUDIO_MODEL',
    defaultModel: 'local-model',
    priority: 80,
    kind: 'local',
    registered: true,
    adapter_implemented: true,
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

const DEFAULT_FALLBACK_CHAIN = Object.freeze([
  'groq',
  'openrouter',
  'openai',
  'anthropic',
  'gemini',
  'ollama',
  'lmstudio',
  'local-heuristic',
]);

const PROVIDER_AUTO_ROUTING_MODES = Object.freeze([
  'auto',
  'auto_fast',
  'auto_cheap',
  'auto_coding',
  'auto_safe',
]);

const AUTO_ROUTING_MODE_WEIGHTS = Object.freeze({
  auto: Object.freeze({
    priority: 0.22,
    availability: 0.24,
    latency: 0.18,
    cost: 0.18,
    coding: 0.1,
    safety: 0.08,
  }),
  auto_fast: Object.freeze({
    priority: 0.08,
    availability: 0.18,
    latency: 0.48,
    cost: 0.08,
    coding: 0.08,
    safety: 0.1,
  }),
  auto_cheap: Object.freeze({
    priority: 0.08,
    availability: 0.18,
    latency: 0.08,
    cost: 0.5,
    coding: 0.06,
    safety: 0.1,
  }),
  auto_coding: Object.freeze({
    priority: 0.08,
    availability: 0.18,
    latency: 0.1,
    cost: 0.08,
    coding: 0.46,
    safety: 0.1,
  }),
  auto_safe: Object.freeze({
    priority: 0.12,
    availability: 0.2,
    latency: 0.08,
    cost: 0.08,
    coding: 0.06,
    safety: 0.46,
  }),
});

const PROVIDER_AUTO_ROUTING_SIGNALS = Object.freeze({
  groq: Object.freeze({
    latency: 0.9,
    cost: 0.9,
    coding: 0.68,
    safety: 0.72,
  }),
  openrouter: Object.freeze({
    latency: 0.7,
    cost: 0.82,
    coding: 0.74,
    safety: 0.76,
  }),
  openai: Object.freeze({
    latency: 0.68,
    cost: 0.58,
    coding: 0.84,
    safety: 0.9,
  }),
  anthropic: Object.freeze({
    latency: 0.56,
    cost: 0.54,
    coding: 0.94,
    safety: 1,
  }),
  gemini: Object.freeze({
    latency: 0.78,
    cost: 0.78,
    coding: 0.72,
    safety: 0.82,
  }),
  ollama: Object.freeze({
    latency: 0.5,
    cost: 1,
    coding: 0.62,
    safety: 0.68,
  }),
  lmstudio: Object.freeze({
    latency: 0.48,
    cost: 1,
    coding: 0.62,
    safety: 0.68,
  }),
});

const FALLBACK_REASONS = Object.freeze({
  REQUESTED_PROVIDER_UNSUPPORTED: 'requested_provider_unsupported',
  REQUESTED_PROVIDER_UNAVAILABLE: 'requested_provider_unavailable',
  NO_REMOTE_PROVIDER_AVAILABLE: 'no_remote_provider_available',
  BYOK_PROVIDER_UNAVAILABLE: 'byok_credentials_incomplete',
  AUTO_ROUTING_NO_CANDIDATE: 'auto_routing_no_valid_candidate',
  POLICY_BLOCKED: 'policy_blocked',
});

function normalizeProviderName(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return normalized || null;
}

function normalizeRoutingMode(value) {
  const normalized = String(value || '').trim().toLowerCase().replace(/[-/]+/g, '_');
  return PROVIDER_AUTO_ROUTING_MODES.includes(normalized) ? normalized : 'legacy';
}

function cleanReason(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.:-]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 96);
}

function safeProviderModel(value) {
  return String(value || '')
    .trim()
    .replace(/[^\w .:/@+-]/g, '')
    .slice(0, 128);
}

function isTruthyEnv(value) {
  return ['1', 'true', 'yes', 'on'].includes(String(value || '').trim().toLowerCase());
}

function readProviderRoutingMode() {
  return normalizeRoutingMode(
    process.env.OMNI_PROVIDER_ROUTING_MODE || process.env.OMINI_PROVIDER_ROUTING_MODE,
  );
}

function normalizePolicyResult(value) {
  if (value == null || value === '') {
    return 'allow';
  }
  if (typeof value === 'string') {
    return ['allow', 'allowed', 'pass', 'ok'].includes(value.trim().toLowerCase())
      ? 'allow'
      : 'block';
  }
  if (typeof value === 'boolean') {
    return value ? 'allow' : 'block';
  }
  if (typeof value === 'object') {
    if (value.allowed === false || value.blocked === true || value.decision === 'block') {
      return 'block';
    }
    return 'allow';
  }
  return 'block';
}

function readByokSessionPolicy() {
  const active = isTruthyEnv(process.env.OMNI_BYOK_SESSION_MODE);
  const provider = normalizeProviderName(process.env.OMNI_BYOK_PROVIDER);
  const failClosed = isTruthyEnv(process.env.OMNI_BYOK_FAIL_CLOSED);
  return {
    active,
    providerName: active ? provider : null,
    failClosed: active && failClosed,
  };
}

function providerSignal(provider, signalName) {
  const signals = PROVIDER_AUTO_ROUTING_SIGNALS[provider?.name] || {};
  const value = Number(signals[signalName]);
  if (!Number.isFinite(value)) {
    return signalName === 'availability' ? (provider?.available ? 1 : 0) : 0.5;
  }
  return Math.max(0, Math.min(1, value));
}

function prioritySignal(provider) {
  const priority = Number(provider?.priority || 99);
  if (!Number.isFinite(priority)) {
    return 0;
  }
  return Math.max(0, Math.min(1, 1 - ((priority - 1) / 100)));
}

function rejection(provider, reason) {
  return {
    provider: normalizeProviderName(provider?.name) || 'unknown',
    model: safeProviderModel(provider?.model),
    reason: cleanReason(reason || 'rejected'),
  };
}

function candidateSnapshot(provider, mode, score = 0) {
  return {
    provider: normalizeProviderName(provider?.name) || 'unknown',
    model: safeProviderModel(provider?.model),
    mode,
    score: Number(Number(score || 0).toFixed(4)),
    available: Boolean(provider?.available),
    policy_result: 'allow',
  };
}

function scoreProviderCandidate(provider, mode) {
  const weights = AUTO_ROUTING_MODE_WEIGHTS[mode] || AUTO_ROUTING_MODE_WEIGHTS.auto;
  const score =
    (weights.priority * prioritySignal(provider))
    + (weights.availability * (provider?.available ? 1 : 0))
    + (weights.latency * providerSignal(provider, 'latency'))
    + (weights.cost * providerSignal(provider, 'cost'))
    + (weights.coding * providerSignal(provider, 'coding'))
    + (weights.safety * providerSignal(provider, 'safety'));
  return Math.max(0, Math.min(1, score));
}

function buildAutoRoutingDecision({
  routingMode = 'auto',
  selected = null,
  candidates = [],
  rejected = [],
  reason = '',
  fallbackUsed = false,
  failClosedReason = '',
  policyResult = 'allow',
} = {}) {
  return {
    routing_mode: routingMode,
    selected_provider: normalizeProviderName(selected?.name) || null,
    selected_model: safeProviderModel(selected?.model),
    candidate_count: Array.isArray(candidates) ? candidates.length : 0,
    decision_reason: cleanReason(reason || (selected ? 'selected_highest_score' : 'no_valid_candidate')),
    fallback_used: Boolean(fallbackUsed),
    rejected_candidates: Array.isArray(rejected) ? rejected.slice(0, 16) : [],
    rejected_reasons: Array.isArray(rejected)
      ? rejected.map(item => cleanReason(item.reason)).filter(Boolean).slice(0, 16)
      : [],
    fail_closed_reason: cleanReason(failClosedReason),
    policy_result: normalizePolicyResult(policyResult),
    created_at: new Date().toISOString(),
  };
}

function selectAutoProvider({ providers = [], routingMode = 'auto', byokPolicy, policyResult = 'allow' } = {}) {
  const normalizedPolicy = normalizePolicyResult(policyResult);
  const rejected = [];

  if (normalizedPolicy !== 'allow') {
    for (const provider of providers) {
      rejected.push(rejection(provider, FALLBACK_REASONS.POLICY_BLOCKED));
    }
    return {
      selected: null,
      candidates: [],
      rejected,
      decision: buildAutoRoutingDecision({
        routingMode,
        rejected,
        reason: FALLBACK_REASONS.POLICY_BLOCKED,
        failClosedReason: FALLBACK_REASONS.POLICY_BLOCKED,
        policyResult: normalizedPolicy,
      }),
    };
  }

  const scopedProviders = byokPolicy?.active
    ? providers.filter(provider => provider.name === byokPolicy.providerName)
    : providers;
  const candidates = [];
  for (const provider of scopedProviders) {
    if (!provider?.registered) {
      rejected.push(rejection(provider, 'provider_not_registered'));
      continue;
    }
    if (!provider.adapter_implemented || provider.execution_status === 'unsupported') {
      rejected.push(rejection(provider, 'provider_adapter_unavailable'));
      continue;
    }
    if (!provider.model_configured) {
      rejected.push(rejection(provider, 'model_unavailable'));
      continue;
    }
    if (!provider.executable || !provider.available) {
      rejected.push(rejection(provider, byokPolicy?.active ? FALLBACK_REASONS.BYOK_PROVIDER_UNAVAILABLE : 'provider_unavailable'));
      continue;
    }
    if (provider.kind === 'embedded') {
      rejected.push(rejection(provider, 'embedded_provider_not_auto_candidate'));
      continue;
    }
    const score = scoreProviderCandidate(provider, routingMode);
    candidates.push({
      provider,
      score,
      snapshot: candidateSnapshot(provider, routingMode, score),
    });
  }

  candidates.sort((a, b) => {
    if (b.score !== a.score) {
      return b.score - a.score;
    }
    return (a.provider.priority || 99) - (b.provider.priority || 99);
  });
  const selected = candidates[0]?.provider || null;
  const failClosedReason = selected ? '' : (
    byokPolicy?.active ? FALLBACK_REASONS.BYOK_PROVIDER_UNAVAILABLE : FALLBACK_REASONS.AUTO_ROUTING_NO_CANDIDATE
  );

  return {
    selected,
    candidates: candidates.map(item => item.snapshot),
    rejected,
    decision: buildAutoRoutingDecision({
      routingMode,
      selected,
      candidates: candidates.map(item => item.snapshot),
      rejected,
      reason: selected ? 'selected_highest_score' : failClosedReason,
      failClosedReason,
      policyResult: normalizedPolicy,
    }),
  };
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
    execution_status: definition.adapter_implemented && configured
      ? 'active'
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
  const raw = envValue('OMNI_AVAILABLE_PROVIDERS') || envValue('OMINI_AVAILABLE_PROVIDERS');
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
  byokSessionMode = false,
  byokProviderName = null,
  byokFailClosed = false,
  routingMode = 'legacy',
  autoRoutingDecision = null,
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
    byokSessionMode: Boolean(byokSessionMode),
    byokProviderName,
    byokFailClosed: Boolean(byokFailClosed),
    routingMode,
    autoRoutingDecision,
  };
}

function resolveProviderRoute({
  complexity = 'simple',
  preferred = '',
  routingMode = '',
  policyResult = 'allow',
} = {}) {
  const normalizedRoutingMode = normalizeRoutingMode(routingMode || readProviderRoutingMode());
  const byokPolicy = readByokSessionPolicy();
  const registry = getProviderRegistry({ includeEmbeddedLocal: true });
  const providersByName = new Map(registry.map(provider => [provider.name, provider]));
  const remoteExecutable = sortProvidersByPolicy(
    registry.filter(provider => provider.kind !== 'embedded' && provider.executable),
  );
  const noRemoteProviderAvailable = remoteExecutable.length === 0;
  const requestedProviderName = byokPolicy.active
    ? byokPolicy.providerName
    : normalizeProviderName(preferred);
  const requestedProvider = requestedProviderName ? providersByName.get(requestedProviderName) : null;

  if (normalizedRoutingMode !== 'legacy') {
    const autoRoute = selectAutoProvider({
      providers: registry,
      routingMode: normalizedRoutingMode,
      byokPolicy,
      policyResult,
    });
    if (autoRoute.selected) {
      return buildRouteOutcome({
        requestedProviderName,
        selectedProviderName: autoRoute.selected.name,
        executionProvider: { ...autoRoute.selected },
        noRemoteProviderAvailable,
        byokSessionMode: Boolean(byokPolicy.active),
        byokProviderName: byokPolicy.active ? byokPolicy.providerName : null,
        byokFailClosed: Boolean(byokPolicy.failClosed),
        routingMode: normalizedRoutingMode,
        autoRoutingDecision: autoRoute.decision,
      });
    }

    return buildRouteOutcome({
      requestedProviderName,
      selectedProviderName: requestedProviderName,
      fallbackTriggered: false,
      fallbackReason: autoRoute.decision.fail_closed_reason || FALLBACK_REASONS.AUTO_ROUTING_NO_CANDIDATE,
      noRemoteProviderAvailable,
      noProviderAvailable: true,
      byokSessionMode: Boolean(byokPolicy.active),
      byokProviderName: byokPolicy.active ? byokPolicy.providerName : null,
      byokFailClosed: Boolean(byokPolicy.failClosed),
      routingMode: normalizedRoutingMode,
      autoRoutingDecision: autoRoute.decision,
    });
  }

  if (byokPolicy.active) {
    if (requestedProvider?.executable && requestedProvider.kind !== 'embedded') {
      return buildRouteOutcome({
        requestedProviderName,
        selectedProviderName: requestedProvider.name,
        executionProvider: { ...requestedProvider },
        noRemoteProviderAvailable,
        byokSessionMode: true,
        byokProviderName: requestedProvider.name,
        byokFailClosed: byokPolicy.failClosed,
        routingMode: normalizedRoutingMode,
      });
    }
    return buildRouteOutcome({
      requestedProviderName,
      selectedProviderName: requestedProviderName,
      fallbackTriggered: false,
      fallbackReason: FALLBACK_REASONS.BYOK_PROVIDER_UNAVAILABLE,
      noRemoteProviderAvailable,
      noProviderAvailable: true,
      byokSessionMode: true,
      byokProviderName: requestedProviderName,
      byokFailClosed: byokPolicy.failClosed,
      routingMode: normalizedRoutingMode,
    });
  }

  if (requestedProvider?.executable) {
    if (requestedProvider.kind === 'embedded') {
      return buildRouteOutcome({
        requestedProviderName,
        selectedProviderName: requestedProvider.name,
        localFallbackProvider: { ...requestedProvider },
        noRemoteProviderAvailable,
        routingMode: normalizedRoutingMode,
      });
    }
    return buildRouteOutcome({
      requestedProviderName,
      selectedProviderName: requestedProvider.name,
      executionProvider: { ...requestedProvider },
      noRemoteProviderAvailable,
      routingMode: normalizedRoutingMode,
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
      routingMode: normalizedRoutingMode,
    });
  }

  const normalizedComplexity = String(complexity || 'simple').trim().toLowerCase();
  const selectedProvider = normalizedComplexity === 'complex'
    ? remoteExecutable.find(provider => provider.kind === 'remote') || remoteExecutable[0]
    : remoteExecutable.find(provider => provider.kind === 'local') || remoteExecutable[0];
  if (selectedProvider) {
    return buildRouteOutcome({
      selectedProviderName: selectedProvider.name,
      executionProvider: { ...selectedProvider },
      noRemoteProviderAvailable,
      routingMode: normalizedRoutingMode,
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
    routingMode: normalizedRoutingMode,
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
  PROVIDER_AUTO_ROUTING_MODES,
  buildProviderDiagnostics,
  chooseProvider,
  getAvailableProviders,
  getProviderRegistry,
  resolveProviderRoute,
};

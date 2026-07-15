import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const providerRouterPath = '../../platform/providers/providerRouter.js';

const providerEnvKeys = [
  'GROQ_API_KEY',
  'GROQ_MODEL',
  'OPENROUTER_API_KEY',
  'OPENROUTER_MODEL',
  'OPENAI_API_KEY',
  'OPENAI_MODEL',
  'ANTHROPIC_API_KEY',
  'ANTHROPIC_MODEL',
  'GEMINI_API_KEY',
  'GEMINI_MODEL',
  'DEEPSEEK_API_KEY',
  'DEEPSEEK_MODEL',
  'OLLAMA_URL',
  'OLLAMA_MODEL',
  'LMSTUDIO_URL',
  'LMSTUDIO_MODEL',
  'OMNI_AVAILABLE_PROVIDERS',
  'OMNI_PROVIDER_ROUTING_MODE',
  'OMNI_BYOK_SESSION_MODE',
  'OMNI_BYOK_PROVIDER',
  'OMNI_BYOK_FAIL_CLOSED',
];

function withProviderEnv(values, fn) {
  const saved = Object.fromEntries(providerEnvKeys.map(key => [key, process.env[key]]));
  for (const key of providerEnvKeys) {
    delete process.env[key];
  }
  Object.assign(process.env, values);
  try {
    delete require.cache[require.resolve(providerRouterPath)];
    return fn(require(providerRouterPath));
  } finally {
    for (const key of providerEnvKeys) {
      if (saved[key] === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = saved[key];
      }
    }
    delete require.cache[require.resolve(providerRouterPath)];
  }
}

function assertRoute(route, expected) {
  for (const [key, value] of Object.entries(expected)) {
    assert.equal(route[key], value, `${key} mismatch`);
  }
}

withProviderEnv({
  GROQ_API_KEY: 'groq-router-fallback-test-key',
  OPENAI_API_KEY: 'openai-router-fallback-test-key',
  OPENROUTER_API_KEY: 'openrouter-router-fallback-test-key',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex', preferred: 'anthropic' });
  assert.equal(route.requestedProviderName, 'anthropic');
  assert.equal(route.selectedProviderName, 'groq');
  assert.equal(route.executionProviderName, 'groq');
  assert.equal(route.executionProvider.name, 'groq');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackProviderName, 'groq');
  assert.equal(route.fallbackTriggered, true);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.REQUESTED_PROVIDER_UNAVAILABLE);
  assert.equal(route.noRemoteProviderAvailable, false);
  assert.equal(route.noProviderAvailable, false);
});

withProviderEnv({
  OPENROUTER_API_KEY: 'openrouter-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex' });
  assert.equal(route.requestedProviderName, null);
  assert.equal(route.selectedProviderName, 'openrouter');
  assert.equal(route.executionProviderName, 'openrouter');
  assert.equal(route.executionProvider.name, 'openrouter');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.noRemoteProviderAvailable, false);
});

withProviderEnv({
  OPENROUTER_API_KEY: 'openrouter-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'openrouter' });
  assert.equal(route.requestedProviderName, 'openrouter');
  assert.equal(route.selectedProviderName, 'openrouter');
  assert.equal(route.executionProviderName, 'openrouter');
  assert.equal(route.fallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, '');
});

withProviderEnv({
  GROQ_API_KEY: 'groq-router-fallback-test-key',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'unknown-provider' });
  assert.equal(route.requestedProviderName, 'unknown-provider');
  assert.equal(route.selectedProviderName, 'groq');
  assert.equal(route.executionProviderName, 'groq');
  assert.equal(route.fallbackTriggered, true);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.REQUESTED_PROVIDER_UNAVAILABLE);
});

withProviderEnv({
  OPENROUTER_API_KEY: 'openrouter-router-fallback-test-key',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'unknown-provider' });
  assert.equal(route.requestedProviderName, 'unknown-provider');
  assert.equal(route.selectedProviderName, 'openrouter');
  assert.equal(route.executionProviderName, 'openrouter');
  assert.equal(route.fallbackProviderName, 'openrouter');
  assert.equal(route.fallbackTriggered, true);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.REQUESTED_PROVIDER_UNAVAILABLE);
});

withProviderEnv({
  OPENAI_API_KEY: 'openai-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex' });
  assert.equal(route.requestedProviderName, null);
  assert.equal(route.selectedProviderName, 'openai');
  assert.equal(route.executionProviderName, 'openai');
  assert.equal(route.executionProvider.name, 'openai');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.noRemoteProviderAvailable, false);
});

withProviderEnv({
  OPENAI_API_KEY: 'openai-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'openai' });
  assert.equal(route.requestedProviderName, 'openai');
  assert.equal(route.selectedProviderName, 'openai');
  assert.equal(route.executionProviderName, 'openai');
  assert.equal(route.fallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, '');
});

withProviderEnv({
  OPENAI_API_KEY: 'openai-router-fallback-test-key',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex', preferred: 'anthropic' });
  assert.equal(route.requestedProviderName, 'anthropic');
  assert.equal(route.selectedProviderName, 'openai');
  assert.equal(route.executionProviderName, 'openai');
  assert.equal(route.executionProvider.name, 'openai');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackProviderName, 'openai');
  assert.equal(route.fallbackTriggered, true);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.REQUESTED_PROVIDER_UNAVAILABLE);
  assert.equal(route.noRemoteProviderAvailable, false);
  assert.equal(route.noProviderAvailable, false);
});

withProviderEnv({
  ANTHROPIC_API_KEY: 'anthropic-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex' });
  assert.equal(route.requestedProviderName, null);
  assert.equal(route.selectedProviderName, 'anthropic');
  assert.equal(route.executionProviderName, 'anthropic');
  assert.equal(route.executionProvider.name, 'anthropic');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.noRemoteProviderAvailable, false);
});

withProviderEnv({
  ANTHROPIC_API_KEY: 'anthropic-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'anthropic' });
  assert.equal(route.requestedProviderName, 'anthropic');
  assert.equal(route.selectedProviderName, 'anthropic');
  assert.equal(route.executionProviderName, 'anthropic');
  assert.equal(route.fallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, '');
});

withProviderEnv({
  GEMINI_API_KEY: 'gemini-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex' });
  assert.equal(route.requestedProviderName, null);
  assert.equal(route.selectedProviderName, 'gemini');
  assert.equal(route.executionProviderName, 'gemini');
  assert.equal(route.executionProvider.name, 'gemini');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.noRemoteProviderAvailable, false);
});

withProviderEnv({
  GEMINI_API_KEY: 'gemini-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'gemini' });
  assert.equal(route.requestedProviderName, 'gemini');
  assert.equal(route.selectedProviderName, 'gemini');
  assert.equal(route.executionProviderName, 'gemini');
  assert.equal(route.fallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, '');
});

withProviderEnv({
  GEMINI_API_KEY: 'gemini-router-fallback-test-key',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex', preferred: 'deepseek' });
  assert.equal(route.requestedProviderName, 'deepseek');
  assert.equal(route.selectedProviderName, 'gemini');
  assert.equal(route.executionProviderName, 'gemini');
  assert.equal(route.executionProvider.name, 'gemini');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackProviderName, 'gemini');
  assert.equal(route.fallbackTriggered, true);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.REQUESTED_PROVIDER_UNSUPPORTED);
  assert.equal(route.noRemoteProviderAvailable, false);
  assert.equal(route.noProviderAvailable, false);
});

withProviderEnv({
  OLLAMA_URL: 'http://127.0.0.1:11434',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex' });
  assert.equal(route.requestedProviderName, null);
  assert.equal(route.selectedProviderName, 'ollama');
  assert.equal(route.executionProviderName, 'ollama');
  assert.equal(route.executionProvider.name, 'ollama');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.noRemoteProviderAvailable, false);
});

withProviderEnv({
  OLLAMA_URL: 'http://127.0.0.1:11434',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'ollama' });
  assert.equal(route.requestedProviderName, 'ollama');
  assert.equal(route.selectedProviderName, 'ollama');
  assert.equal(route.executionProviderName, 'ollama');
  assert.equal(route.fallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, '');
});

withProviderEnv({
  LMSTUDIO_URL: 'http://127.0.0.1:1234',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex' });
  assert.equal(route.requestedProviderName, null);
  assert.equal(route.selectedProviderName, 'lmstudio');
  assert.equal(route.executionProviderName, 'lmstudio');
  assert.equal(route.executionProvider.name, 'lmstudio');
  assert.equal(route.localFallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.noRemoteProviderAvailable, false);
});

withProviderEnv({
  LMSTUDIO_URL: 'http://127.0.0.1:1234',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'lmstudio' });
  assert.equal(route.requestedProviderName, 'lmstudio');
  assert.equal(route.selectedProviderName, 'lmstudio');
  assert.equal(route.executionProviderName, 'lmstudio');
  assert.equal(route.fallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, '');
});

withProviderEnv({
  LMSTUDIO_URL: 'http://127.0.0.1:1234',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex', preferred: 'ollama' });
  assert.equal(route.requestedProviderName, 'ollama');
  assert.equal(route.selectedProviderName, 'lmstudio');
  assert.equal(route.executionProviderName, 'lmstudio');
  assert.equal(route.fallbackProviderName, 'lmstudio');
  assert.equal(route.fallbackTriggered, true);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.REQUESTED_PROVIDER_UNAVAILABLE);
  assert.equal(route.noRemoteProviderAvailable, false);
  assert.equal(route.noProviderAvailable, false);
});

withProviderEnv({}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex' });
  assert.equal(route.requestedProviderName, null);
  assert.equal(route.selectedProviderName, 'local-heuristic');
  assert.equal(route.executionProvider, null);
  assert.equal(route.executionProviderName, null);
  assert.equal(route.localFallbackProviderName, 'local-heuristic');
  assert.equal(route.fallbackTriggered, true);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.NO_REMOTE_PROVIDER_AVAILABLE);
  assert.equal(route.noRemoteProviderAvailable, true);
  assert.equal(route.noProviderAvailable, false);
});

withProviderEnv({
  GROQ_API_KEY: 'groq-router-fallback-test-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'complex', preferred: 'groq' });
  assert.equal(route.requestedProviderName, 'groq');
  assert.equal(route.selectedProviderName, 'groq');
  assert.equal(route.executionProviderName, 'groq');
  assert.equal(route.fallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, '');
});

withProviderEnv({
  OMNI_BYOK_SESSION_MODE: 'true',
  OMNI_BYOK_PROVIDER: 'openai',
  OMNI_BYOK_FAIL_CLOSED: 'true',
  GROQ_API_KEY: 'system-groq-key',
  OPENAI_API_KEY: 'session-openai-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'groq' });
  assert.equal(route.byokSessionMode, true);
  assert.equal(route.byokFailClosed, true);
  assert.equal(route.requestedProviderName, 'openai');
  assert.equal(route.selectedProviderName, 'openai');
  assert.equal(route.executionProviderName, 'openai');
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackProvider, null);
});

withProviderEnv({
  OMNI_BYOK_SESSION_MODE: 'true',
  OMNI_BYOK_PROVIDER: 'openai',
  OMNI_BYOK_FAIL_CLOSED: 'true',
  GROQ_API_KEY: 'system-groq-key',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ complexity: 'simple', preferred: 'groq' });
  assert.equal(route.byokSessionMode, true);
  assert.equal(route.requestedProviderName, 'openai');
  assert.equal(route.selectedProviderName, 'openai');
  assert.equal(route.executionProvider, null);
  assert.equal(route.executionProviderName, null);
  assert.equal(route.fallbackProvider, null);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.BYOK_PROVIDER_UNAVAILABLE);
  assert.equal(route.noProviderAvailable, true);
});

[
  {
    label: 'no remote or local provider selects local heuristic',
    env: {},
    input: { complexity: 'complex' },
    expected: {
      selectedProviderName: 'local-heuristic',
      executionProviderName: null,
      localFallbackProviderName: 'local-heuristic',
      fallbackTriggered: true,
      fallbackReason: 'no_remote_provider_available',
      noRemoteProviderAvailable: true,
      noProviderAvailable: false,
    },
  },
  {
    label: 'only groq configured selects groq',
    env: { GROQ_API_KEY: 'groq-router-matrix-key' },
    input: { complexity: 'complex' },
    expected: {
      selectedProviderName: 'groq',
      executionProviderName: 'groq',
      fallbackTriggered: false,
      fallbackReason: '',
      noRemoteProviderAvailable: false,
      noProviderAvailable: false,
    },
  },
  {
    label: 'groq preferred with openrouter also configured stays on groq',
    env: {
      GROQ_API_KEY: 'groq-router-matrix-key',
      OPENROUTER_API_KEY: 'openrouter-router-matrix-key',
    },
    input: { complexity: 'complex', preferred: 'groq' },
    expected: {
      requestedProviderName: 'groq',
      selectedProviderName: 'groq',
      executionProviderName: 'groq',
      fallbackTriggered: false,
      fallbackReason: '',
    },
  },
  {
    label: 'groq unavailable falls through to openrouter',
    env: { OPENROUTER_API_KEY: 'openrouter-router-matrix-key' },
    input: { complexity: 'complex', preferred: 'groq' },
    expected: {
      requestedProviderName: 'groq',
      selectedProviderName: 'openrouter',
      executionProviderName: 'openrouter',
      fallbackProviderName: 'openrouter',
      fallbackTriggered: true,
      fallbackReason: 'requested_provider_unavailable',
    },
  },
  {
    label: 'openrouter unavailable falls through to openai',
    env: { OPENAI_API_KEY: 'openai-router-matrix-key' },
    input: { complexity: 'complex', preferred: 'openrouter' },
    expected: {
      requestedProviderName: 'openrouter',
      selectedProviderName: 'openai',
      executionProviderName: 'openai',
      fallbackProviderName: 'openai',
      fallbackTriggered: true,
      fallbackReason: 'requested_provider_unavailable',
    },
  },
  {
    label: 'all remotes unavailable selects local heuristic',
    env: {},
    input: { complexity: 'complex', preferred: 'openai' },
    expected: {
      requestedProviderName: 'openai',
      selectedProviderName: 'local-heuristic',
      executionProviderName: null,
      localFallbackProviderName: 'local-heuristic',
      fallbackProviderName: 'local-heuristic',
      fallbackTriggered: true,
      fallbackReason: 'requested_provider_unavailable',
      noRemoteProviderAvailable: true,
      noProviderAvailable: false,
    },
  },
  {
    label: 'deepseek unsupported falls through to first executable provider',
    env: {
      OPENAI_API_KEY: 'openai-router-matrix-key',
      DEEPSEEK_API_KEY: 'deepseek-router-matrix-key',
    },
    input: { complexity: 'complex', preferred: 'deepseek' },
    expected: {
      requestedProviderName: 'deepseek',
      selectedProviderName: 'openai',
      executionProviderName: 'openai',
      fallbackTriggered: true,
      fallbackReason: 'requested_provider_unsupported',
    },
  },
  {
    label: 'unrecognized provider falls through to first executable provider',
    env: { ANTHROPIC_API_KEY: 'anthropic-router-matrix-key' },
    input: { complexity: 'complex', preferred: 'not-a-provider' },
    expected: {
      requestedProviderName: 'not-a-provider',
      selectedProviderName: 'anthropic',
      executionProviderName: 'anthropic',
      fallbackProviderName: 'anthropic',
      fallbackTriggered: true,
      fallbackReason: 'requested_provider_unavailable',
    },
  },
  {
    label: 'ollama url makes ollama selectable',
    env: { OLLAMA_URL: 'http://127.0.0.1:11434' },
    input: { complexity: 'complex' },
    expected: {
      selectedProviderName: 'ollama',
      executionProviderName: 'ollama',
      fallbackTriggered: false,
      noRemoteProviderAvailable: false,
    },
  },
  {
    label: 'lmstudio url makes lmstudio selectable',
    env: { LMSTUDIO_URL: 'http://127.0.0.1:1234' },
    input: { complexity: 'complex' },
    expected: {
      selectedProviderName: 'lmstudio',
      executionProviderName: 'lmstudio',
      fallbackTriggered: false,
      noRemoteProviderAvailable: false,
    },
  },
  {
    label: 'ollama without url is skipped',
    env: { LMSTUDIO_URL: 'http://127.0.0.1:1234' },
    input: { complexity: 'complex', preferred: 'ollama' },
    expected: {
      requestedProviderName: 'ollama',
      selectedProviderName: 'lmstudio',
      executionProviderName: 'lmstudio',
      fallbackTriggered: true,
      fallbackReason: 'requested_provider_unavailable',
    },
  },
  {
    label: 'lmstudio without url is skipped',
    env: {},
    input: { complexity: 'complex', preferred: 'lmstudio' },
    expected: {
      requestedProviderName: 'lmstudio',
      selectedProviderName: 'local-heuristic',
      executionProviderName: null,
      fallbackTriggered: true,
      fallbackReason: 'requested_provider_unavailable',
      noRemoteProviderAvailable: true,
    },
  },
  {
    label: 'byok inactive preserves normal fallback',
    env: {
      GROQ_API_KEY: 'groq-router-matrix-key',
      OMNI_BYOK_SESSION_MODE: 'false',
      OMNI_BYOK_PROVIDER: 'openai',
      OMNI_BYOK_FAIL_CLOSED: 'true',
    },
    input: { complexity: 'complex', preferred: 'openai' },
    expected: {
      requestedProviderName: 'openai',
      selectedProviderName: 'groq',
      executionProviderName: 'groq',
      byokSessionMode: false,
      fallbackTriggered: true,
      fallbackReason: 'requested_provider_unavailable',
    },
  },
  {
    label: 'byok active unknown provider fails closed',
    env: {
      OMNI_BYOK_SESSION_MODE: 'true',
      OMNI_BYOK_PROVIDER: 'unknown-provider',
      OMNI_BYOK_FAIL_CLOSED: 'true',
      GROQ_API_KEY: 'system-groq-router-matrix-key',
    },
    input: { complexity: 'complex', preferred: 'groq' },
    expected: {
      requestedProviderName: 'unknown-provider',
      selectedProviderName: 'unknown-provider',
      executionProviderName: null,
      fallbackProviderName: null,
      fallbackTriggered: false,
      fallbackReason: 'byok_credentials_incomplete',
      byokSessionMode: true,
      byokFailClosed: true,
      noProviderAvailable: true,
    },
  },
  {
    label: 'byok active deepseek fails closed',
    env: {
      OMNI_BYOK_SESSION_MODE: 'true',
      OMNI_BYOK_PROVIDER: 'deepseek',
      OMNI_BYOK_FAIL_CLOSED: 'true',
      DEEPSEEK_API_KEY: 'deepseek-router-matrix-key',
      GROQ_API_KEY: 'system-groq-router-matrix-key',
    },
    input: { complexity: 'complex', preferred: 'groq' },
    expected: {
      requestedProviderName: 'deepseek',
      selectedProviderName: 'deepseek',
      executionProviderName: null,
      fallbackProviderName: null,
      fallbackTriggered: false,
      fallbackReason: 'byok_credentials_incomplete',
      byokSessionMode: true,
      byokFailClosed: true,
      noProviderAvailable: true,
    },
  },
].forEach((testCase) => {
  withProviderEnv(testCase.env, ({ resolveProviderRoute }) => {
    const route = resolveProviderRoute(testCase.input);
    assertRoute(route, testCase.expected);
  });
});

withProviderEnv({
  GROQ_API_KEY: 'groq-auto-fast-key',
  OPENAI_API_KEY: 'openai-auto-fast-key',
}, ({ PROVIDER_AUTO_ROUTING_MODES, resolveProviderRoute }) => {
  assert.deepEqual(PROVIDER_AUTO_ROUTING_MODES, ['auto', 'auto_fast', 'auto_cheap', 'auto_coding', 'auto_safe']);
  const route = resolveProviderRoute({ routingMode: 'auto_fast' });
  assert.equal(route.routingMode, 'auto_fast');
  assert.equal(route.selectedProviderName, 'groq');
  assert.equal(route.executionProviderName, 'groq');
  assert.equal(route.autoRoutingDecision.routing_mode, 'auto_fast');
  assert.equal(route.autoRoutingDecision.selected_provider, 'groq');
  assert.equal(route.autoRoutingDecision.fail_closed_reason, '');
  assert.equal(route.autoRoutingDecision.policy_result, 'allow');
});

withProviderEnv({
  GROQ_API_KEY: 'groq-auto-cheap-key',
  OPENROUTER_API_KEY: 'openrouter-auto-cheap-key',
  OPENAI_API_KEY: 'openai-auto-cheap-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ routingMode: 'auto_cheap' });
  assert.equal(route.selectedProviderName, 'groq');
  assert.equal(route.executionProviderName, 'groq');
  assert.equal(route.autoRoutingDecision.decision_reason, 'selected_highest_score');
});

withProviderEnv({
  ANTHROPIC_API_KEY: 'anthropic-auto-coding-key',
  OPENAI_API_KEY: 'openai-auto-coding-key',
  GROQ_API_KEY: 'groq-auto-coding-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ routingMode: 'auto_coding' });
  assert.equal(route.selectedProviderName, 'anthropic');
  assert.equal(route.executionProviderName, 'anthropic');
});

withProviderEnv({
  ANTHROPIC_API_KEY: 'anthropic-auto-safe-key',
  OPENAI_API_KEY: 'openai-auto-safe-key',
  GROQ_API_KEY: 'groq-auto-safe-key',
}, ({ resolveProviderRoute }) => {
  const route = resolveProviderRoute({ routingMode: 'auto_safe' });
  assert.equal(route.selectedProviderName, 'anthropic');
  assert.equal(route.executionProviderName, 'anthropic');
});

withProviderEnv({
  GROQ_API_KEY: 'groq-auto-policy-key',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ routingMode: 'auto', policyResult: 'block' });
  assert.equal(route.executionProviderName, null);
  assert.equal(route.noProviderAvailable, true);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.POLICY_BLOCKED);
  assert.equal(route.autoRoutingDecision.fail_closed_reason, FALLBACK_REASONS.POLICY_BLOCKED);
  assert.equal(route.autoRoutingDecision.policy_result, 'block');
  assert.equal(JSON.stringify(route).includes('groq-auto-policy-key'), false);
});

withProviderEnv({
  OMNI_BYOK_SESSION_MODE: 'true',
  OMNI_BYOK_PROVIDER: 'openai',
  OMNI_BYOK_FAIL_CLOSED: 'true',
  GROQ_API_KEY: 'system-groq-auto-key',
}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ routingMode: 'auto_safe' });
  assert.equal(route.requestedProviderName, 'openai');
  assert.equal(route.executionProviderName, null);
  assert.equal(route.noProviderAvailable, true);
  assert.equal(route.fallbackTriggered, false);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.BYOK_PROVIDER_UNAVAILABLE);
  assert.equal(route.autoRoutingDecision.fail_closed_reason, FALLBACK_REASONS.BYOK_PROVIDER_UNAVAILABLE);
  assert.equal(JSON.stringify(route).includes('system-groq-auto-key'), false);
});

withProviderEnv({}, ({ FALLBACK_REASONS, resolveProviderRoute }) => {
  const route = resolveProviderRoute({ routingMode: 'auto' });
  assert.equal(route.executionProviderName, null);
  assert.equal(route.localFallbackProviderName, null);
  assert.equal(route.noProviderAvailable, true);
  assert.equal(route.fallbackReason, FALLBACK_REASONS.AUTO_ROUTING_NO_CANDIDATE);
  assert.equal(route.autoRoutingDecision.fail_closed_reason, FALLBACK_REASONS.AUTO_ROUTING_NO_CANDIDATE);
  assert.equal(route.autoRoutingDecision.rejected_candidates.some(item => item.reason === 'provider_unavailable'), true);
});

console.log('providerRouterFallback tests passed');

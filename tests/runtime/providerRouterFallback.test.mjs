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
  'OMINI_AVAILABLE_PROVIDERS',
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

console.log('providerRouterFallback tests passed');

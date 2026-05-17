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

withProviderEnv({}, ({ DEFAULT_FALLBACK_CHAIN, FALLBACK_REASONS, getProviderRegistry, chooseProvider }) => {
  assert.deepEqual(DEFAULT_FALLBACK_CHAIN, ['groq', 'openrouter', 'openai', 'anthropic', 'local-heuristic']);
  assert.deepEqual(Object.values(FALLBACK_REASONS).sort(), [
    'no_remote_provider_available',
    'requested_provider_unavailable',
    'requested_provider_unsupported',
  ]);
  const rows = getProviderRegistry();
  assert.deepEqual(rows.map(row => row.name), [
    'groq',
    'openrouter',
    'openai',
    'anthropic',
    'gemini',
    'deepseek',
    'ollama',
    'lmstudio',
  ]);
  const openrouter = rows.find(item => item.name === 'openrouter');
  assert.equal(openrouter.registered, true);
  assert.equal(openrouter.adapter_implemented, true);
  assert.equal(openrouter.executable, false);
  assert.equal(openrouter.execution_status, 'credential_gated');
  assert.equal(openrouter.model, 'openai/gpt-4o-mini');
  const openai = rows.find(item => item.name === 'openai');
  assert.equal(openai.registered, true);
  assert.equal(openai.adapter_implemented, true);
  assert.equal(openai.executable, false);
  assert.equal(openai.execution_status, 'credential_gated');
  assert.equal(openai.model, 'gpt-4o-mini');
  const anthropic = rows.find(item => item.name === 'anthropic');
  assert.equal(anthropic.registered, true);
  assert.equal(anthropic.adapter_implemented, true);
  assert.equal(anthropic.executable, false);
  assert.equal(anthropic.execution_status, 'credential_gated');
  assert.equal(anthropic.model, 'claude-haiku-4-5-20251001');
  for (const name of ['gemini', 'deepseek']) {
    const row = rows.find(item => item.name === name);
    assert.equal(row.registered, true);
    assert.equal(row.adapter_implemented, false);
    assert.equal(row.executable, false);
    assert.equal(row.execution_status, 'unsupported');
  }
  for (const name of ['ollama', 'lmstudio']) {
    const row = rows.find(item => item.name === name);
    assert.equal(row.registered, true);
    assert.equal(row.adapter_implemented, false);
    assert.equal(row.executable, false);
    assert.equal(row.execution_status, 'local_config_gated');
  }
  assert.equal(chooseProvider({ complexity: 'complex' }).name, 'local-heuristic');
});

withProviderEnv({
  OPENAI_API_KEY: 'openai-provider-router-test-key',
  OPENROUTER_API_KEY: 'openrouter-provider-router-test-key',
  ANTHROPIC_API_KEY: 'anthropic-provider-router-test-key',
  GROQ_API_KEY: 'groq-provider-router-test-key',
  OMINI_AVAILABLE_PROVIDERS: 'openai,openrouter,groq',
}, ({ buildProviderDiagnostics, chooseProvider, getAvailableProviders }) => {
  const selected = chooseProvider({ complexity: 'complex' });
  assert.equal(selected.name, 'groq');
  assert.deepEqual(getAvailableProviders().map(row => row.name), ['groq', 'openrouter', 'openai', 'anthropic', 'local-heuristic']);

  const rows = buildProviderDiagnostics({
    selectedProviderName: 'openai',
    attemptedProviderName: 'openai',
    failureClass: 'provider_timeout',
    failureReason: 'request timed out',
  });
  const openai = rows.find(row => row.provider === 'openai');
  assert.equal(openai.configured, true);
  assert.equal(openai.key_present, true);
  assert.equal(openai.adapter_implemented, true);
  assert.equal(openai.available, true);
  assert.equal(openai.execution_status, 'active');

  const openrouter = rows.find(row => row.provider === 'openrouter');
  assert.equal(openrouter.configured, true);
  assert.equal(openrouter.key_present, true);
  assert.equal(openrouter.adapter_implemented, true);
  assert.equal(openrouter.available, true);
  assert.equal(openrouter.execution_status, 'active');

  const anthropic = rows.find(row => row.provider === 'anthropic');
  assert.equal(anthropic.configured, true);
  assert.equal(anthropic.key_present, true);
  assert.equal(anthropic.adapter_implemented, true);
  assert.equal(anthropic.available, true);
  assert.equal(anthropic.execution_status, 'active');

  const groq = rows.find(row => row.provider === 'groq');
  assert.equal(groq.configured, true);
  assert.equal(groq.adapter_implemented, true);
  assert.equal(groq.available, true);
  assert.equal(groq.execution_status, 'active');

  const serialized = JSON.stringify(rows).toLowerCase();
  assert.equal(serialized.includes('openai-provider-router-test-key'), false);
  assert.equal(serialized.includes('openrouter-provider-router-test-key'), false);
  assert.equal(serialized.includes('anthropic-provider-router-test-key'), false);
  assert.equal(serialized.includes('groq-provider-router-test-key'), false);
  assert.equal(serialized.includes('raw_config'), false);
});

console.log('providerRouterMetadata tests passed');

import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const supabaseClientPath = path.join(projectRoot, 'storage', 'memory', 'supabaseClient.js');
const providerRouterPath = path.join(projectRoot, 'platform', 'providers', 'providerRouter.js');

function withEnv(values, fn) {
  const keys = Object.keys(values);
  const saved = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  for (const key of keys) {
    if (values[key] === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = values[key];
    }
  }
  try {
    return fn();
  } finally {
    for (const key of keys) {
      if (saved[key] === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = saved[key];
      }
    }
  }
}

delete require.cache[require.resolve(supabaseClientPath)];
const supabaseClient = require(supabaseClientPath);

assert.equal(Object.prototype.hasOwnProperty.call(supabaseClient, 'supabaseKey'), false);
assert.equal(Object.prototype.hasOwnProperty.call(supabaseClient, 'supabaseUrl'), false);
assert.equal(Object.prototype.hasOwnProperty.call(supabaseClient, 'raw_key'), false);
assert.equal(Object.prototype.hasOwnProperty.call(supabaseClient, 'raw_url'), false);

const supabaseDiagnostics = supabaseClient.getSupabaseDiagnostics();
assert.deepEqual(Object.keys(supabaseDiagnostics).sort(), [
  'anon_key_present',
  'service_role_present',
  'supabase_configured',
  'url_present',
]);
for (const value of Object.values(supabaseDiagnostics)) {
  assert.equal(typeof value, 'boolean');
}

withEnv({
  OPENAI_API_KEY: 'openai-secret-value',
  OPENAI_MODEL: 'gpt-test',
  ANTHROPIC_API_KEY: undefined,
  GROQ_API_KEY: undefined,
  GEMINI_API_KEY: undefined,
  DEEPSEEK_API_KEY: undefined,
}, () => {
  delete require.cache[require.resolve(providerRouterPath)];
  const { buildProviderDiagnostics } = require(providerRouterPath);
  const rows = buildProviderDiagnostics({
    selectedProviderName: 'openai',
    attemptedProviderName: 'openai',
    failureClass: 'provider_timeout',
    failureReason: 'provider did not respond',
  });
  const openai = rows.find(row => row.provider === 'openai');
  assert.equal(openai.configured, true);
  assert.equal(openai.key_present, true);
  assert.equal(openai.model_configured, true);
  const serialized = JSON.stringify(rows).toLowerCase();
  assert.equal(serialized.includes('openai-secret-value'), false);
  assert.equal(serialized.includes('key_prefix'), false);
  assert.equal(serialized.includes('key_length'), false);
  assert.equal(serialized.includes('key_hash'), false);
  assert.equal(serialized.includes('raw_config'), false);
  assert.equal(serialized.includes('env'), false);
});

console.log('secrets config hardening: ok');

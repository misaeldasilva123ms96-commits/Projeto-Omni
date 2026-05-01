import assert from 'node:assert/strict';
import path from 'node:path';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const Module = require('node:module');
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const runtimeMemoryStorePath = path.join(projectRoot, 'storage', 'memory', 'runtimeMemoryStore.js');
const supabaseClientPath = path.join(projectRoot, 'storage', 'memory', 'supabaseClient.js');

for (const key of [
  'SUPABASE_URL',
  'SUPABASE_ANON_KEY',
  'VITE_SUPABASE_URL',
  'VITE_SUPABASE_ANON_KEY',
  'VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY',
]) {
  delete process.env[key];
}

const runtimeMemoryStore = require(runtimeMemoryStorePath);
const cwd = mkdtempSync(path.join(tmpdir(), 'omni-memory-supabase-optional-'));

try {
  const memory = runtimeMemoryStore.getSessionRuntimeMemory(cwd, 'supabase-optional-test');

  assert.equal(memory.vector_backend, 'local-file');
  assert.equal(memory.vector_diagnostics.supabase_configured, false);
  assert.equal(memory.vector_diagnostics.url_present, false);
  assert.equal(memory.vector_diagnostics.anon_key_present, false);
  assert.equal(typeof runtimeMemoryStore.recordSemanticEntry, 'function');

  runtimeMemoryStore.recordSemanticEntry(cwd, 'supabase-optional-test', {
    path: 'package.json',
    preview: 'local semantic memory should work without the Supabase package',
    source: 'test',
  });

  const updated = runtimeMemoryStore.getSessionRuntimeMemory(cwd, 'supabase-optional-test');
  assert.equal(updated.vector_backend, 'local-file');
  assert.equal(updated.semantic_candidates.length, 1);
} finally {
  rmSync(cwd, { recursive: true, force: true });
}

delete require.cache[supabaseClientPath];
process.env.SUPABASE_URL = 'https://example.supabase.co';
process.env.SUPABASE_ANON_KEY = 'public-anon-key';
const originalLoad = Module._load;
let createdWith = null;

try {
  Module._load = function patchedLoad(request, parent, isMain) {
    if (request === '@supabase/supabase-js') {
      return {
        createClient(url, key, options) {
          createdWith = { url, key, options };
          return { from: () => ({ insert: async () => ({ error: null }) }) };
        },
      };
    }
    return originalLoad.call(this, request, parent, isMain);
  };

  const supabaseClient = require(supabaseClientPath);

  assert.equal(supabaseClient.isSupabaseConfigured(), true);
  assert.deepEqual(supabaseClient.getSupabaseDiagnostics(), {
    supabase_configured: true,
    url_present: true,
    anon_key_present: true,
    service_role_present: false,
  });
  assert.equal(createdWith.url, 'https://example.supabase.co');
  assert.equal(createdWith.key, 'public-anon-key');
  assert.equal(createdWith.options.auth.persistSession, false);
} finally {
  Module._load = originalLoad;
  delete process.env.SUPABASE_URL;
  delete process.env.SUPABASE_ANON_KEY;
  delete require.cache[supabaseClientPath];
}

console.log('supabase-optional-memory: ok');

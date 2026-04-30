import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '../..');
const clientPath = path.join(projectRoot, 'storage', 'memory', 'supabaseClient.js');

const script = `
const assert = require('node:assert/strict');
const Module = require('node:module');
const clientPath = ${JSON.stringify(clientPath)};
const originalLoad = Module._load;

delete require.cache[require.resolve(clientPath)];
Module._load = function patchedLoad(request, parent, isMain) {
  if (request === '@supabase/supabase-js') {
    const error = new Error("Cannot find module '@supabase/supabase-js'");
    error.code = 'MODULE_NOT_FOUND';
    throw error;
  }
  return originalLoad.call(this, request, parent, isMain);
};

try {
  const client = require(clientPath);

  assert.equal(client.isSupabaseConfigured(), false);
  assert.equal(client.supabase, null);
  assert.deepEqual(client.getSupabaseDiagnostics(), {
    backend: 'local-file',
    available: false,
    configured: false,
    package_available: false,
    reason: 'package_missing',
    package: '@supabase/supabase-js',
  });
} finally {
  Module._load = originalLoad;
  delete require.cache[require.resolve(clientPath)];
}
`;

const completed = spawnSync('node', ['-e', script], {
  cwd: projectRoot,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe'],
});

assert.equal(completed.status, 0, completed.stderr || completed.stdout);

console.log('supabase optional runtime dependency test: ok');

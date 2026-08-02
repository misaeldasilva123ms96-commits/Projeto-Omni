import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  DIAGNOSTICS_AUTHORIZATION_MARKER,
  publishSanitizedDiagnostics,
  sanitizeDiagnosticText,
  validateChatText,
  validateErrorText,
  validateHealthText,
  validateStatusText,
  verifyDiagnosticPublication,
} from '../../scripts/docker-runtime-smoke-validator.mjs';

process.env.OMNI_SMOKE_SENTINEL = 'sentinel-fixture-123456789';
process.env.OMNI_SMOKE_AUTH_MATERIAL = 'auth-fixture-123456789';

test('accepts canonical sanitized health, status, chat, and public error fixtures', () => {
  validateHealthText(JSON.stringify({ status: 'ok', rust_service: 'ok', runtime_session_version: 1, python: { observable: true }, node: { observable: true } }));
  validateStatusText(JSON.stringify({ api_version: '1', status: 'ok', runtime_mode: 'live', rust_service: 'omni-api', python_status: 'not_checked', node_status: 'observable', runtime_session_version: 1 }));
  validateChatText(JSON.stringify({ response: 'Olá!', session_id: 's1', source: 'python-subprocess', runtime_session_version: 1, client_session_id: 'docker-smoke-client', cognitive_runtime_inspection: { runtime_mode: 'DIRECT_LOCAL_RESPONSE', provider_actual: 'local-heuristic', llm_provider_attempted: false, llm_provider_succeeded: false, tool_invoked: false, tool_executed: false, runtime_truth: { runtime_mode: 'PROVIDER_UNAVAILABLE', llm_provider_attempted: false, llm_provider_succeeded: false, tool_invoked: false, tool_executed: false } } }));
  validateErrorText(JSON.stringify({ error_public_code: 'INVALID_JSON', error_public_message: 'Invalid JSON.', internal_error_redacted: true }), 'INVALID_JSON');
});

test('rejects sentinel, traceback, host path, operator fields, and false Runtime Truth', () => {
  assert.throws(() => validateHealthText(`{"status":"ok","detail":"${process.env.OMNI_SMOKE_SENTINEL}"}`), /leaked/);
  assert.throws(() => validateStatusText(JSON.stringify({ api_version: '1', status: 'ok', runtime_mode: 'live', rust_service: 'omni-api', python_status: 'not_checked', node_status: 'observable', runtime_session_version: 1, configured_bin: '/app/bin' })), /operator-only/);
  assert.throws(() => validateChatText(JSON.stringify({ response: 'x', session_id: 's', source: 'x', runtime_session_version: 1, client_session_id: 'docker-smoke-client', cognitive_runtime_inspection: { runtime_mode: 'FULL_COGNITIVE_RUNTIME' } })), /DIRECT_LOCAL_RESPONSE/);
  assert.throws(() => validateErrorText('{"error":"Traceback (most recent call last)\\n  /home/runner/work/repo/x.py"}', 'INVALID_JSON'), /traceback|runner path/i);
});

test('sanitizes synthetic and authorization material before diagnostics publication', () => {
  const sanitized = sanitizeDiagnosticText(`token=${process.env.OMNI_SMOKE_AUTH_MATERIAL}\nAuthorization: Bearer abcdef123456\n${process.env.OMNI_SMOKE_SENTINEL}\n/home/runner/work/repo/file\nC:\\Users\\runner\\repo`);
  assert(!sanitized.includes(process.env.OMNI_SMOKE_AUTH_MATERIAL));
  assert(!sanitized.includes(process.env.OMNI_SMOKE_SENTINEL));
  assert(!sanitized.includes('abcdef123456'));
  assert(!sanitized.includes('/home/runner/work'));
  assert(!sanitized.includes('C:\\Users'));
});

function withDiagnosticFixture(run) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'omni-diagnostics-test-'));
  const rawDir = path.join(root, 'raw');
  const publicationDir = path.join(root, 'publication');
  fs.mkdirSync(rawDir);
  try {
    run({ rawDir, publicationDir });
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

test('authorizes publication only after every selected diagnostic is sanitized and scanned', () => {
  withDiagnosticFixture(({ rawDir, publicationDir }) => {
    fs.writeFileSync(path.join(rawDir, 'docker-version.txt'), 'Docker 29.0\n');
    fs.writeFileSync(path.join(rawDir, 'container-logs.txt'), `token=${process.env.OMNI_SMOKE_AUTH_MATERIAL}\nhealthy\n`);

    const result = publishSanitizedDiagnostics(rawDir, publicationDir);
    const published = fs.readdirSync(publicationDir).sort();

    assert.equal(result.selectedFiles, 2);
    assert.equal(verifyDiagnosticPublication(publicationDir).safeFiles, 2);
    assert(published.includes(DIAGNOSTICS_AUTHORIZATION_MARKER));
    assert.equal(fs.readFileSync(path.join(publicationDir, DIAGNOSTICS_AUTHORIZATION_MARKER), 'utf8'), 'diagnostics_verified=true\n');
    assert(published.includes('container-logs-sanitized.txt'));
    assert(published.includes('docker-version-sanitized.txt'));
    assert(!published.includes('container-logs.txt'));
    assert(!fs.readFileSync(path.join(publicationDir, 'container-logs-sanitized.txt'), 'utf8').includes(process.env.OMNI_SMOKE_AUTH_MATERIAL));
  });
});

test('rejects symlinks and raw filenames even when a marker is present', () => {
  withDiagnosticFixture(({ rawDir, publicationDir }) => {
    fs.writeFileSync(path.join(rawDir, 'compose-ps.txt'), 'safe state');
    publishSanitizedDiagnostics(rawDir, publicationDir);

    fs.writeFileSync(path.join(publicationDir, 'compose-ps.txt'), 'raw copy');
    assert.throws(() => verifyDiagnosticPublication(publicationDir), /raw diagnostic filename/);
    fs.rmSync(path.join(publicationDir, 'compose-ps.txt'));

    const outside = path.join(path.dirname(publicationDir), 'outside');
    fs.mkdirSync(outside);
    fs.writeFileSync(path.join(outside, 'private.txt'), 'safe outside content');
    fs.symlinkSync(outside, path.join(publicationDir, 'escape-sanitized'), 'junction');
    assert.throws(() => verifyDiagnosticPublication(publicationDir), /regular files|symbolic links/);
  });
});

test('rejects an unsafe fixture without publishing raw files or an authorization marker', () => {
  withDiagnosticFixture(({ rawDir, publicationDir }) => {
    const unsafe = [
      'Traceback (most recent call last)',
      "thread 'main' panicked at src/main.rs:1",
      process.env.OMNI_SMOKE_SENTINEL,
      `Authorization: Bearer ${process.env.OMNI_SMOKE_AUTH_MATERIAL}`,
      '/home/runner/work/Projeto-Omni/private.log',
      'C:\\Users\\runner\\private.log',
    ].join('\n');
    fs.writeFileSync(path.join(rawDir, 'container-logs.txt'), unsafe);

    assert.throws(() => publishSanitizedDiagnostics(rawDir, publicationDir), /traceback|panic/i);
    assert(!fs.existsSync(path.join(publicationDir, DIAGNOSTICS_AUTHORIZATION_MARKER)));
    assert(!fs.existsSync(path.join(publicationDir, 'container-logs.txt')));
    assert(!fs.existsSync(publicationDir));
  });
});

test('sanitizer failure injection withholds the entire publication directory', () => {
  withDiagnosticFixture(({ rawDir, publicationDir }) => {
    fs.writeFileSync(path.join(rawDir, 'compose-ps.txt'), 'container state');

    assert.throws(
      () => publishSanitizedDiagnostics(rawDir, publicationDir, { sanitize: () => { throw new Error('injected sanitizer failure'); } }),
      /injected sanitizer failure/,
    );
    assert(!fs.existsSync(publicationDir));
    assert(!fs.existsSync(path.join(publicationDir, DIAGNOSTICS_AUTHORIZATION_MARKER)));
  });
});

test('Docker workflow pull-request paths include the Docker build-context control file', () => {
  const workflow = fs.readFileSync(new URL('../../.github/workflows/docker-build-ci.yml', import.meta.url), 'utf8');
  const pullRequestBlock = workflow.match(/  pull_request:\r?\n(?<body>[\s\S]*?)  workflow_dispatch:/)?.groups?.body;
  assert(pullRequestBlock, 'pull_request workflow block is missing');
  const paths = [...pullRequestBlock.matchAll(/^      - "([^"]+)"$/gm)].map((match) => match[1]);
  assert(paths.includes('.dockerignore'), '.dockerignore must trigger Docker Runtime Smoke');
});

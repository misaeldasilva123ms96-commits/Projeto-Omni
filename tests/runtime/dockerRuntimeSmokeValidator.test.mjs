import assert from 'node:assert/strict';
import test from 'node:test';

import {
  sanitizeDiagnosticText,
  validateChatText,
  validateErrorText,
  validateHealthText,
  validateStatusText,
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

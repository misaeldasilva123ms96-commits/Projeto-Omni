import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function invariant(condition, message) {
  if (!condition) throw new Error(message);
}

function nonEmpty(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function requiredNumber(value, name) {
  invariant(Number.isInteger(value) && value > 0, `${name} must be a positive integer`);
}

function forbiddenPublicText(text) {
  const exactValues = [process.env.OMNI_SMOKE_SENTINEL, process.env.OMNI_SMOKE_AUTH_MATERIAL]
    .filter(Boolean);
  for (const value of exactValues) {
    invariant(!text.includes(value), 'synthetic smoke material leaked');
  }
  const patterns = [
    [/\bTraceback \(most recent call last\)/i, 'Python traceback'],
    [/\bthread ['"][^'"\r\n]+['"] panicked\b|\bpanicked at\b/i, 'Rust panic'],
    [/\b(?:Error|Exception):[^\r\n]*\n\s+at\s+/i, 'Node stack trace'],
    [/\/home\/runner\/work\//i, 'GitHub runner path'],
    [/[A-Za-z]:[\\/](?:Users|Windows|Program Files)[\\/]/i, 'Windows host path'],
    [/Authorization\s*:\s*Bearer\s+\S+/i, 'authorization token'],
    [/(?:api[_-]?key|token|secret)\s*[=:]\s*['"]?[A-Za-z0-9_\-]{16,}/i, 'credential-like value'],
  ];
  for (const [pattern, label] of patterns) {
    invariant(!pattern.test(text), `${label} leaked`);
  }
}

function parsePublicJson(text) {
  forbiddenPublicText(text);
  let value;
  try {
    value = JSON.parse(text);
  } catch (error) {
    throw new Error(`response is not valid JSON: ${error.message}`);
  }
  invariant(value && typeof value === 'object' && !Array.isArray(value), 'response must be a JSON object');
  return value;
}

function containsKey(value, forbidden) {
  if (Array.isArray(value)) return value.some((item) => containsKey(item, forbidden));
  if (!value || typeof value !== 'object') return false;
  return Object.entries(value).some(([key, child]) => forbidden.has(key) || containsKey(child, forbidden));
}

export function validateHealthText(text) {
  const body = parsePublicJson(text);
  invariant(nonEmpty(body.status), 'health.status is missing');
  invariant(body.status === 'ok', 'health.status must be ok');
  invariant(nonEmpty(body.rust_service), 'health.rust_service is missing');
  invariant(body.rust_service === 'ok', 'health.rust_service must report the canonical Omni API state');
  requiredNumber(body.runtime_session_version, 'health.runtime_session_version');
  invariant(body.python && typeof body.python === 'object', 'health.python dependency state is missing');
  invariant(body.node && typeof body.node === 'object', 'health.node dependency state is missing');
  return body;
}

export function validateStatusText(text) {
  const body = parsePublicJson(text);
  invariant(String(body.api_version) === '1', 'status.api_version must be 1');
  invariant(nonEmpty(body.status), 'status.status is missing');
  invariant(nonEmpty(body.runtime_mode), 'status.runtime_mode is missing');
  invariant(nonEmpty(body.rust_service), 'status.rust_service is missing');
  invariant(nonEmpty(body.python_status), 'status.python_status is missing');
  invariant(nonEmpty(body.node_status), 'status.node_status is missing');
  requiredNumber(body.runtime_session_version, 'status.runtime_session_version');
  invariant(!containsKey(body, new Set(['configured_bin', 'entry'])), 'operator-only path field leaked in public status');
  return body;
}

export function validateChatText(text, { apiV1 = false } = {}) {
  const body = parsePublicJson(text);
  if (apiV1) invariant(String(body.api_version) === '1', 'chat.api_version must be 1');
  invariant(nonEmpty(body.response), 'chat.response is empty');
  invariant(nonEmpty(body.session_id), 'chat.session_id is missing');
  invariant(nonEmpty(body.source), 'chat.source is missing');
  requiredNumber(body.runtime_session_version, 'chat.runtime_session_version');
  invariant(body.client_session_id === 'docker-smoke-client', 'chat correlation was not preserved');
  const inspection = body.cognitive_runtime_inspection;
  invariant(inspection && typeof inspection === 'object', 'Runtime Truth inspection is missing');
  const mode = inspection.runtime_mode;
  const nestedMode = inspection.runtime_truth?.runtime_mode;
  invariant(mode === 'DIRECT_LOCAL_RESPONSE', `expected deterministic DIRECT_LOCAL_RESPONSE, received ${String(mode)}`);
  invariant(nestedMode === 'PROVIDER_UNAVAILABLE', `expected truthful PROVIDER_UNAVAILABLE evidence, received ${String(nestedMode)}`);
  invariant(inspection.provider_actual === 'local-heuristic', 'deterministic chat must use the local heuristic provider');
  const serialized = JSON.stringify(inspection);
  invariant(!/FULL_COGNITIVE_RUNTIME/.test(serialized), 'matcher response falsely claims full cognitive execution');
  for (const signals of [inspection, inspection.runtime_truth]) {
    for (const key of ['llm_provider_attempted', 'llm_provider_succeeded', 'tool_invoked', 'tool_executed']) {
      invariant(signals?.[key] === false, `local Runtime Truth ${key} must be false`);
    }
  }
  return body;
}

export function validateErrorText(text, expectedCode) {
  const body = parsePublicJson(text);
  invariant(body.error_public_code === expectedCode, `expected ${expectedCode}, received ${String(body.error_public_code)}`);
  invariant(nonEmpty(body.error_public_message), 'public error message is missing');
  invariant(body.internal_error_redacted === true, 'public error must mark internal detail redacted');
  return body;
}

export function sanitizeDiagnosticText(text) {
  let sanitized = String(text);
  for (const value of [process.env.OMNI_SMOKE_SENTINEL, process.env.OMNI_SMOKE_AUTH_MATERIAL].filter(Boolean)) {
    sanitized = sanitized.split(value).join('[REDACTED]');
  }
  sanitized = sanitized
    .replace(/Authorization\s*:\s*Bearer\s+\S+/gi, 'Authorization: Bearer [REDACTED]')
    .replace(/((?:api[_-]?key|token|secret)\s*[=:]\s*['"]?)[^\s,'"}]+/gi, '$1[REDACTED]')
    .replace(/\/home\/runner\/work\/[^\s'"}]*/gi, '[HOST_PATH_REDACTED]')
    .replace(/[A-Za-z]:[\\/](?:Users|Windows|Program Files)[\\/][^\s'"}]*/gi, '[HOST_PATH_REDACTED]');
  return sanitized;
}

function cli() {
  const [command, input, extra] = process.argv.slice(2);
  invariant(command && input, 'usage: validator <health|status|chat|chat-v1|error|sanitize|scan|scan-dir> <path> [value]');
  if (command === 'scan-dir') {
    for (const entry of fs.readdirSync(input, { recursive: true })) {
      const candidate = path.join(input, entry);
      if (fs.statSync(candidate).isFile()) forbiddenPublicText(fs.readFileSync(candidate, 'utf8'));
    }
    return;
  }
  const text = fs.readFileSync(input, 'utf8');
  if (command === 'scan') {
    forbiddenPublicText(text);
    return;
  }
  if (command === 'sanitize') {
    invariant(extra, 'sanitize requires an output path');
    fs.writeFileSync(extra, sanitizeDiagnosticText(text));
    return;
  }
  if (command === 'health') validateHealthText(text);
  else if (command === 'status') validateStatusText(text);
  else if (command === 'chat') validateChatText(text);
  else if (command === 'chat-v1') validateChatText(text, { apiV1: true });
  else if (command === 'error') validateErrorText(text, extra);
  else throw new Error(`unknown command: ${command}`);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  try { cli(); } catch (error) { console.error(`docker smoke validation failed: ${error.message}`); process.exitCode = 1; }
}

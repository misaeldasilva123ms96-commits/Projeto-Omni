'use strict';

const http = require('http');
const {
  OMNI_ERROR_CODE,
  buildPublicError,
} = require('../runtime/tooling/errorTaxonomy');
const runner = require('./queryEngineRunner');

const DEFAULT_HOST = '127.0.0.1';
const DEFAULT_PORT = 7020;
const MAX_SERVICE_BODY_BYTES = 65_536;

const DANGEROUS_KEY_PATTERN = /(stack|trace|traceback|env|api_key|token|jwt|secret|password|authorization|bearer|command|args|argv|stdout|stderr|raw|payload|execution_request|memory_content|memory_raw|provider_raw|raw_response|tool_raw_result)/i;
const UNIX_PATH_PATTERN = /(?:\/home|\/root|\/tmp|\/var|\/usr|\/etc)\/[^\s"'`]+/g;
const WINDOWS_PATH_PATTERN = /(?:[A-Za-z]:\\(?:Users|Windows|Program Files)[^\s"'`]*)/g;
const API_KEY_PATTERN = /\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b/g;
const BEARER_PATTERN = /\bBearer\s+[A-Za-z0-9._~+/=-]{10,}\b/gi;
const JWT_PATTERN = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g;

function envValue(primary, legacy, fallback) {
  const primaryValue = String(process.env[primary] || '').trim();
  if (primaryValue) return primaryValue;
  const legacyValue = String(process.env[legacy] || '').trim();
  if (legacyValue) return legacyValue;
  return fallback;
}

function getServiceConfig() {
  const rawPort = Number.parseInt(envValue('OMNI_NODE_SERVICE_PORT', 'OMINI_NODE_SERVICE_PORT', String(DEFAULT_PORT)), 10);
  const port = Number.isFinite(rawPort) ? Math.max(1, Math.min(65535, rawPort)) : DEFAULT_PORT;
  return {
    host: envValue('OMNI_NODE_SERVICE_HOST', 'OMINI_NODE_SERVICE_HOST', DEFAULT_HOST),
    port,
  };
}

function sanitizeString(value) {
  return String(value)
    .replace(UNIX_PATH_PATTERN, '[REDACTED_PATH]')
    .replace(WINDOWS_PATH_PATTERN, '[REDACTED_PATH]')
    .replace(API_KEY_PATTERN, '[REDACTED_API_KEY]')
    .replace(BEARER_PATTERN, 'Bearer [REDACTED_TOKEN]')
    .replace(JWT_PATTERN, '[REDACTED_JWT]');
}

function sanitizePublicPayload(input, depth = 0) {
  if (depth > 12) return '[REDACTED_INTERNAL_PAYLOAD]';
  if (input == null || typeof input === 'boolean' || typeof input === 'number') return input;
  if (typeof input === 'string') return sanitizeString(input);
  if (Array.isArray(input)) return input.map((item) => sanitizePublicPayload(item, depth + 1));
  if (typeof input !== 'object') return undefined;

  const out = {};
  for (const [key, value] of Object.entries(input)) {
    if (DANGEROUS_KEY_PATTERN.test(key)) {
      continue;
    }
    out[key] = sanitizePublicPayload(value, depth + 1);
  }
  return out;
}

function healthPayload() {
  return {
    ok: true,
    service: 'node-query-engine',
    mode: 'service',
  };
}

function readinessPayload() {
  return {
    ok: true,
    service: 'node-query-engine',
    checks: {
      query_engine_runner_importable: true,
      public_sanitizer: true,
      cli_subprocess_entrypoint_preserved: true,
    },
  };
}

function buildServiceError(code, status, reason) {
  const publicError = buildPublicError(code);
  return [
    status,
    sanitizePublicPayload({
      ok: false,
      service: 'node-query-engine',
      mode: 'service',
      response: '',
      error: publicError,
      ...publicError,
      runtime_truth: {
        runtime_mode: code === OMNI_ERROR_CODE.NODE_RUNNER_FAILED ? 'NODE_FALLBACK' : 'SAFE_FALLBACK',
        fallback_triggered: true,
        error_public_code: publicError.error_public_code,
        internal_error_redacted: true,
      },
      reason,
    }),
  ];
}

function buildRunnerPayload(input) {
  const runtimeContext = input.runtime_context && typeof input.runtime_context === 'object'
    ? input.runtime_context
    : {};
  const metadata = input.metadata && typeof input.metadata === 'object'
    ? input.metadata
    : {};
  const session = runtimeContext.session && typeof runtimeContext.session === 'object'
    ? { ...runtimeContext.session }
    : {};

  if (typeof input.session_id === 'string') session.session_id = input.session_id;
  if (typeof input.request_id === 'string') session.request_id = input.request_id;
  if (Object.keys(metadata).length > 0) session.metadata = metadata;

  return {
    message: String(input.message || '').trim(),
    memory: runtimeContext.memory && typeof runtimeContext.memory === 'object' ? runtimeContext.memory : {},
    history: Array.isArray(runtimeContext.history) ? runtimeContext.history : [],
    summary: typeof runtimeContext.summary === 'string' ? runtimeContext.summary : '',
    capabilities: Array.isArray(runtimeContext.capabilities) ? runtimeContext.capabilities : [],
    session,
    memoryContext: {
      user: runtimeContext.memory && typeof runtimeContext.memory === 'object' ? runtimeContext.memory : {},
      agentMemory: typeof runtimeContext.agentMemory === 'string' ? runtimeContext.agentMemory : '',
    },
    cwd: runner.getWorkspaceRoot(),
  };
}

async function handleRunPayload(input, runtime = runner) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return buildServiceError(OMNI_ERROR_CODE.INPUT_VALIDATION_FAILED, 400, 'request_body_must_be_object');
  }

  const message = String(input.message || '').trim();
  if (!message) {
    return buildServiceError(OMNI_ERROR_CODE.INPUT_VALIDATION_FAILED, 400, 'message_required');
  }

  try {
    const execution = await runtime.tryRunExistingQueryEngineDetailed(buildRunnerPayload({ ...input, message }));
    const publicResult = runtime.sanitizeForUser(execution.result);
    const safe = sanitizePublicPayload(publicResult);
    safe.service = 'node-query-engine';
    safe.mode = 'service';
    return [200, safe];
  } catch {
    return buildServiceError(OMNI_ERROR_CODE.NODE_RUNNER_FAILED, 500, 'query_engine_failed');
  }
}

function writeJson(response, status, payload) {
  const body = Buffer.from(JSON.stringify(sanitizePublicPayload(payload)), 'utf8');
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': String(body.length),
  });
  response.end(body);
}

function readRequestBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    request.on('data', (chunk) => {
      total += chunk.length;
      if (total > MAX_SERVICE_BODY_BYTES) {
        reject(new Error('payload_too_large'));
        request.destroy();
        return;
      }
      chunks.push(chunk);
    });
    request.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    request.on('error', reject);
  });
}

function createServer() {
  return http.createServer(async (request, response) => {
    const url = new URL(request.url || '/', 'http://127.0.0.1');
    if (request.method === 'GET' && url.pathname === '/internal/query-engine/health') {
      writeJson(response, 200, healthPayload());
      return;
    }
    if (request.method === 'GET' && url.pathname === '/internal/query-engine/readiness') {
      writeJson(response, 200, readinessPayload());
      return;
    }
    if (request.method !== 'POST' || url.pathname !== '/internal/query-engine/run') {
      writeJson(response, ...buildServiceError(OMNI_ERROR_CODE.INPUT_VALIDATION_FAILED, 404, 'not_found'));
      return;
    }

    const contentType = String(request.headers['content-type'] || '').toLowerCase();
    if (!contentType.includes('application/json')) {
      writeJson(response, ...buildServiceError(OMNI_ERROR_CODE.INVALID_CONTENT_TYPE, 415, 'invalid_content_type'));
      return;
    }

    let raw = '';
    try {
      raw = await readRequestBody(request);
    } catch {
      writeJson(response, ...buildServiceError(OMNI_ERROR_CODE.PAYLOAD_TOO_LARGE, 413, 'invalid_body_size'));
      return;
    }

    try {
      writeJson(response, ...(await handleRunPayload(JSON.parse(raw))));
    } catch {
      writeJson(response, ...buildServiceError(OMNI_ERROR_CODE.INVALID_JSON, 400, 'invalid_json'));
    }
  });
}

function main() {
  const config = getServiceConfig();
  const server = createServer();
  server.listen(config.port, config.host, () => {
    process.stderr.write(`node query engine service listening on ${config.host}:${config.port}\n`);
  });
}

module.exports = {
  buildRunnerPayload,
  createServer,
  getServiceConfig,
  handleRunPayload,
  healthPayload,
  readinessPayload,
  sanitizePublicPayload,
};

if (require.main === module) {
  main();
}

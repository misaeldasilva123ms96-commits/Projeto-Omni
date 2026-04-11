'use strict';

const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

let Ajv2020 = null;
try {
  Ajv2020 = require('ajv/dist/2020');
} catch {
  Ajv2020 = null;
}

const MAX_MEMORY_BYTES = 16 * 1024;
const USER_FALLBACK_RESPONSE = 'Entendido. Como posso ajudá-lo?';
const RESPONSE_CANDIDATE_KEYS = ['response', 'message', 'text', 'answer', 'output', 'result'];

function getBaseDir() {
  return process.env.BASE_DIR
    ? path.resolve(process.env.BASE_DIR)
    : path.resolve(__dirname, '..');
}

function loadRunnerSchema() {
  const baseDir = getBaseDir();
  const schemaPath = process.env.RUNNER_SCHEMA_PATH
    ? path.resolve(process.env.RUNNER_SCHEMA_PATH)
    : path.join(baseDir, 'contract', 'runner-schema.v1.json');

  return JSON.parse(fs.readFileSync(schemaPath, 'utf8'));
}

const validatePayload = (() => {
  if (!Ajv2020) {
    return candidate => (
      candidate &&
      typeof candidate.message === 'string' &&
      Array.isArray(candidate.history) &&
      Array.isArray(candidate.capabilities) &&
      candidate.memory &&
      typeof candidate.memory === 'object' &&
      candidate.session &&
      typeof candidate.session === 'object'
    );
  }

  const ajv = new Ajv2020({ allErrors: true, allowUnionTypes: true });
  return ajv.compile(loadRunnerSchema());
})();

function getRawInput() {
  return process.argv.slice(2).join(' ').trim();
}

function getWorkspaceRoot() {
  return process.env.NODE_RUNNER_BASE_DIR
    ? path.resolve(process.env.NODE_RUNNER_BASE_DIR)
    : getBaseDir();
}

function emptyPayload() {
  return {
    message: '',
    memory: {},
    history: [],
    summary: '',
    capabilities: [],
    session: {},
  };
}

function parsePayloadCandidate(rawInput) {
  const attempts = [rawInput];

  if (rawInput.includes('\\"')) {
    attempts.push(rawInput.replace(/\\"/g, '"'));
  }

  if ((rawInput.startsWith('"') && rawInput.endsWith('"')) || (rawInput.startsWith("'") && rawInput.endsWith("'"))) {
    attempts.push(rawInput.slice(1, -1));
  }

  for (const candidate of attempts) {
    try {
      return JSON.parse(candidate);
    } catch {
      continue;
    }
  }

  if (rawInput.startsWith('{\\') && rawInput.endsWith('}')) {
    const pseudoJson = rawInput.slice(1, -1);
    const parsed = {};
    for (const part of pseudoJson.split('\\,')) {
      if (!part) {
        continue;
      }
      const [rawKey, ...rawValueParts] = part.split('\\:');
      if (!rawKey || rawValueParts.length === 0) {
        continue;
      }
      const key = rawKey.replace(/^\\+/, '').trim();
      const value = rawValueParts.join('\\:').replace(/^\\+/, '').trim();
      if (key) {
        parsed[key] = value;
      }
    }
    if (Object.keys(parsed).length > 0) {
      return parsed;
    }
  }

  throw new Error('invalid_payload');
}

function safeParsePayload(rawInput) {
  if (!rawInput) {
    return emptyPayload();
  }

  try {
    const parsed = parsePayloadCandidate(rawInput);
    const candidate = {
      message: typeof parsed.message === 'string' ? parsed.message.trim() : '',
      memory: parsed.memory && typeof parsed.memory === 'object' ? parsed.memory : {},
      history: Array.isArray(parsed.history) ? parsed.history : [],
      summary: typeof parsed.summary === 'string' ? parsed.summary.trim() : '',
      capabilities: Array.isArray(parsed.capabilities) ? parsed.capabilities : [],
      session: parsed.session && typeof parsed.session === 'object'
        ? parsed.session
        : (
            typeof parsed.session_id === 'string' && parsed.session_id.trim()
              ? { session_id: parsed.session_id.trim() }
              : {}
          ),
    };

    if (!validatePayload(candidate)) {
      return emptyPayload();
    }

    return candidate;
  } catch {
    return emptyPayload();
  }
}

function readFileIfPresent(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8').trim();
  } catch {
    return '';
  }
}

function collectMemoryFiles(dirPath) {
  if (!dirPath || !fs.existsSync(dirPath)) {
    return [];
  }

  const entries = [];
  const stack = [dirPath];

  while (stack.length > 0) {
    const current = stack.pop();
    let dirEntries = [];

    try {
      dirEntries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const entry of dirEntries) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(absolute);
      } else if (entry.isFile() && entry.name.toUpperCase() === 'MEMORY.MD') {
        entries.push(absolute);
      }
    }
  }

  return entries;
}

function loadAgentMemoryContext() {
  const workspaceRoot = getWorkspaceRoot();
  const candidateDirs = [
    path.join(workspaceRoot, '.claude', 'agent-memory'),
    path.join(workspaceRoot, '.claude', 'agent-memory-local'),
  ];

  const parts = [];
  let totalBytes = 0;

  for (const dirPath of candidateDirs) {
    const files = collectMemoryFiles(dirPath);
    for (const filePath of files) {
      const content = readFileIfPresent(filePath);
      if (!content) {
        continue;
      }

      const chunk = `# ${path.basename(path.dirname(filePath))}\n${content}\n`;
      totalBytes += Buffer.byteLength(chunk, 'utf8');
      if (totalBytes > MAX_MEMORY_BYTES) {
        return parts.join('\n\n');
      }
      parts.push(chunk);
    }
  }

  return parts.join('\n\n');
}

function getQueryEngineCandidates() {
  const workspaceRoot = getWorkspaceRoot();
  const adapterPath = process.env.RUNNER_ADAPTER_PATH
    ? path.resolve(process.env.RUNNER_ADAPTER_PATH)
    : path.join(workspaceRoot, 'src', 'queryEngineRunnerAdapter.js');
  const esmAdapterPath = adapterPath.replace(/\.js$/i, '.mjs');

  return [
    esmAdapterPath,
    adapterPath,
    path.join(workspaceRoot, 'src', 'QueryEngine.js'),
    path.join(workspaceRoot, 'src', 'QueryEngine.ts'),
    path.join(workspaceRoot, 'runtime', 'node', 'QueryEngine.js'),
    path.join(workspaceRoot, 'runtime', 'node', 'QueryEngine.ts'),
    path.join(workspaceRoot, 'dist', 'QueryEngine.js'),
    path.join(workspaceRoot, 'build', 'QueryEngine.js'),
  ];
}

async function runAgentLoop(runner, payload) {
  return runner({
    message: payload.message,
    memoryContext: payload.memoryContext,
    history: payload.history,
    summary: payload.summary,
    capabilities: payload.capabilities,
    session: payload.session,
    cwd: payload.cwd,
  });
}

async function tryRunExistingQueryEngineDetailed(payload) {
  const candidateErrors = [];
  let attemptedTypescriptCandidate = false;
  const attemptedCandidates = [];

  for (const candidate of getQueryEngineCandidates()) {
    if (!fs.existsSync(candidate)) {
      continue;
    }
    attemptedCandidates.push(candidate);
    if (candidate.endsWith('.ts')) {
      attemptedTypescriptCandidate = true;
    }

    try {
      const imported = await import(pathToFileURL(candidate).href);
      const runner =
        imported.runQueryEngine ||
        imported.run ||
        imported.default;

      if (typeof runner !== 'function') {
        continue;
      }

      const result = await runAgentLoop(runner, payload);
      if (result) {
        return {
          result,
          selectedCandidate: candidate,
          attemptedCandidates,
          attemptedTypescriptCandidate,
          candidateErrors,
        };
      }
    } catch (error) {
      candidateErrors.push({
        candidate,
        error_name: error && error.name ? error.name : 'Error',
        error_message: error && error.message ? String(error.message) : String(error || ''),
      });
      continue;
    }
  }

  return {
    result: '',
    selectedCandidate: '',
    attemptedCandidates,
    attemptedTypescriptCandidate,
    candidateErrors,
  };
}

async function tryRunExistingQueryEngine(payload) {
  const execution = await tryRunExistingQueryEngineDetailed(payload);
  return toLegacyRunnerString(execution.result);
}

function toLegacyRunnerString(result) {
  if (typeof result === 'string') {
    return result.trim();
  }

  if (result && typeof result === 'object') {
    if (result.execution_request) {
      return JSON.stringify(result);
    }
    if (typeof result.finalAnswer === 'string') {
      return result.finalAnswer.trim();
    }
    for (const key of RESPONSE_CANDIDATE_KEYS) {
      const value = result[key];
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
    }
  }

  return '';
}

function emitRunnerError(kind, message, details = {}) {
  process.stderr.write(
    JSON.stringify({
      kind,
      message,
      details,
    }),
  );
  process.exit(1);
}

function isDebugLoggingEnabled() {
  const level = String(process.env.OMINI_LOG_LEVEL || process.env.LOG_LEVEL || '').toLowerCase().trim();
  return level === 'debug';
}

function debugLogInternal(stage, payload) {
  if (!isDebugLoggingEnabled()) {
    return;
  }

  try {
    process.stderr.write(`${JSON.stringify({ stage, payload })}\n`);
  } catch {
    // Never break user-visible output because debug logging failed.
  }
}

function tryParseStructuredString(value) {
  if (typeof value !== 'string') {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const looksStructured =
    (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
    (trimmed.startsWith('[') && trimmed.endsWith(']'));

  if (!looksStructured) {
    return null;
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

function sanitizeForUserInternal(input) {
  if (typeof input === 'string') {
    const trimmed = input.trim();
    if (!trimmed) {
      return { response: USER_FALLBACK_RESPONSE };
    }
    const parsed = tryParseStructuredString(trimmed);
    if (parsed !== null) {
      return sanitizeForUserInternal(parsed);
    }
    return { response: trimmed };
  }

  if (input == null || Array.isArray(input)) {
    return { response: USER_FALLBACK_RESPONSE };
  }

  if (typeof input === 'object') {
    for (const key of RESPONSE_CANDIDATE_KEYS) {
      const candidate = input[key];
      if (typeof candidate !== 'string') {
        continue;
      }
      const trimmed = candidate.trim();
      if (!trimmed) {
        continue;
      }
      const parsed = tryParseStructuredString(trimmed);
      if (parsed !== null) {
        return sanitizeForUserInternal(parsed);
      }
      return { response: trimmed };
    }
  }

  return { response: USER_FALLBACK_RESPONSE };
}

function sanitizeForUser(input) {
  debugLogInternal('node_runner_pre_sanitize', input);
  try {
    return sanitizeForUserInternal(input);
  } catch {
    return { response: USER_FALLBACK_RESPONSE };
  }
}

async function main() {
  try {
    const parsed = safeParsePayload(getRawInput());
    if (!parsed.message) {
      process.stdout.write(JSON.stringify({ response: USER_FALLBACK_RESPONSE }));
      return;
    }

    const payload = {
      message: parsed.message,
      memory: parsed.memory,
      history: parsed.history,
      summary: parsed.summary,
      capabilities: parsed.capabilities,
      session: parsed.session,
      memoryContext: {
        user: parsed.memory,
        agentMemory: loadAgentMemoryContext(),
      },
      cwd: getWorkspaceRoot(),
    };

    const execution = await tryRunExistingQueryEngineDetailed(payload);
    debugLogInternal('node_runner_execution_detail', execution);
    if (!execution.result) {
      debugLogInternal('node_runner_missing_result', {
        kind: 'module_resolution_error',
        attempted_candidates: execution.attemptedCandidates,
        selected_candidate: execution.selectedCandidate,
        attempted_typescript_candidate: execution.attemptedTypescriptCandidate,
        candidate_errors: execution.candidateErrors.slice(0, 6),
        cwd: payload.cwd,
      });
      process.stdout.write(JSON.stringify({ response: USER_FALLBACK_RESPONSE }));
      return;
    }

    process.stdout.write(JSON.stringify(sanitizeForUser(execution.result)));
  } catch (error) {
    debugLogInternal('node_runner_main_exception', {
      error_name: error && error.name ? error.name : 'Error',
      error_message: error && error.message ? String(error.message) : String(error || ''),
    });
    process.stdout.write(JSON.stringify({ response: USER_FALLBACK_RESPONSE }));
  }
}

module.exports = {
  emptyPayload,
  getBaseDir,
  getQueryEngineCandidates,
  getWorkspaceRoot,
  loadAgentMemoryContext,
  loadRunnerSchema,
  main,
  safeParsePayload,
  tryRunExistingQueryEngineDetailed,
  tryRunExistingQueryEngine,
  validatePayload,
};

if (require.main === module) {
  main().catch((error) => {
    emitRunnerError('subprocess_exception', 'Unhandled Node runner exception.', {
      error_name: error && error.name ? error.name : 'Error',
      error_message: error && error.message ? String(error.message) : String(error || ''),
    });
  });
}

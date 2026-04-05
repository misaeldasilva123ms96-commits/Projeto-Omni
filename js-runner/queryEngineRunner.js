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
  return (process.argv[2] || '').trim();
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

function safeParsePayload(rawInput) {
  if (!rawInput) {
    return emptyPayload();
  }

  try {
    const parsed = JSON.parse(rawInput);
    const candidate = {
      message: typeof parsed.message === 'string' ? parsed.message.trim() : '',
      memory: parsed.memory && typeof parsed.memory === 'object' ? parsed.memory : {},
      history: Array.isArray(parsed.history) ? parsed.history : [],
      summary: typeof parsed.summary === 'string' ? parsed.summary.trim() : '',
      capabilities: Array.isArray(parsed.capabilities) ? parsed.capabilities : [],
      session: parsed.session && typeof parsed.session === 'object' ? parsed.session : {},
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
    path.join(workspaceRoot, 'dist', 'QueryEngine.js'),
    path.join(workspaceRoot, 'build', 'QueryEngine.js'),
  ];
}

async function runAgentLoop(runner, payload) {
  const result = await runner({
    message: payload.message,
    memoryContext: payload.memoryContext,
    history: payload.history,
    summary: payload.summary,
    capabilities: payload.capabilities,
    session: payload.session,
    cwd: payload.cwd,
  });

  if (typeof result === 'string') {
    return result.trim();
  }

  if (result && result.execution_request) {
    return JSON.stringify(result);
  }

  if (result && typeof result.finalAnswer === 'string') {
    return result.finalAnswer.trim();
  }

  if (result && typeof result.response === 'string') {
    return result.response.trim();
  }

  return '';
}

async function tryRunExistingQueryEngine(payload) {
  for (const candidate of getQueryEngineCandidates()) {
    if (!fs.existsSync(candidate)) {
      continue;
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
        return result;
      }
    } catch {
      continue;
    }
  }

  return '';
}

async function main() {
  const parsed = safeParsePayload(getRawInput());
  if (!parsed.message) {
    process.stdout.write('');
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

  const response = await tryRunExistingQueryEngine(payload);
  process.stdout.write(response || '');
}

main().catch(() => {
  process.stdout.write('');
});

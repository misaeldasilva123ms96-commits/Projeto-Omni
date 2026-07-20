import { mkdtempSync, mkdirSync, rmSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { basename, dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SUITES = Object.freeze({
  backend: 'backend/python/tests',
  runtime: 'tests',
})
const SENSITIVE_ENV = /(?:^|_)(?:API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS?)$/i
const SENSITIVE_PREFIX = /^(?:OPENAI|ANTHROPIC|DEEPSEEK|GEMINI|GROQ|MISTRAL|SUPABASE|AZURE|AWS|GITHUB)_/i

export function aggregateExitCode(results) {
  return results.every((result) => result === 0) ? 0 : 1
}

export function selectedSuites(selection) {
  if (selection === 'all') return ['backend', 'runtime']
  if (Object.hasOwn(SUITES, selection)) return [selection]
  throw new Error(`Unknown Python test suite: ${selection}`)
}

function gitStatus() {
  const result = spawnSync('git', ['status', '--porcelain=v1'], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  })
  if (result.status !== 0) {
    throw new Error('Unable to capture repository status for test-isolation verification.')
  }
  return result.stdout
}

function isolatedEnvironment(root) {
  const env = {}
  for (const [key, value] of Object.entries(process.env)) {
    if (value === undefined || SENSITIVE_ENV.test(key) || SENSITIVE_PREFIX.test(key)) continue
    env[key] = value
  }

  const roots = {
    OMNI_MEMORY_ROOT: join(root, 'memory'),
    OMNI_MEMORY_DIR: join(root, 'memory'),
    OMNI_MEMORY_JSON_PATH: join(root, 'memory', 'memory.json'),
    OMNI_JSONL_MEMORY_PATH: join(root, 'memory', 'audit.jsonl'),
    OMNI_SQLITE_MEMORY_PATH: join(root, 'memory', 'memory.sqlite'),
    OMNI_CACHE_ROOT: join(root, 'cache'),
    OMNI_ARTIFACT_ROOT: join(root, 'artifacts'),
    OMNI_LOG_ROOT: join(root, 'logs'),
    OMNI_DATABASE_ROOT: join(root, 'databases'),
    OMNI_CREDENTIAL_ROOT: join(root, 'credentials'),
    OMNI_PROVIDER_STATE_ROOT: join(root, 'providers'),
    OMNI_RUNTIME_SESSION_ROOT: join(root, 'sessions'),
    OMNI_UPLOAD_ROOT: join(root, 'uploads'),
    OMNI_WORKSPACE_ROOT: REPO_ROOT,
  }
  for (const path of [...Object.values(roots), join(root, 'home'), join(root, 'tmp')]) {
    mkdirSync(path, { recursive: true })
  }

  return {
    ...env,
    ...roots,
    OMNI_TEST_MODE: 'true',
    OMNI_ENABLE_SQLITE_MEMORY: 'false',
    HOME: join(root, 'home'),
    USERPROFILE: join(root, 'home'),
    TEMP: join(root, 'tmp'),
    TMP: join(root, 'tmp'),
    GIT_CONFIG_GLOBAL: process.platform === 'win32' ? 'NUL' : '/dev/null',
    PYTHONDONTWRITEBYTECODE: '1',
  }
}

function runSuite(name) {
  const isolationParent = dirname(REPO_ROOT)
  mkdirSync(isolationParent, { recursive: true })
  const isolationPrefix = `.omni-python-${name}-${process.pid}-`
  const isolationRoot = mkdtempSync(join(isolationParent, isolationPrefix))
  const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3')
  const args = [
    '-m',
    'pytest',
    '-q',
    SUITES[name],
    `--basetemp=${join(isolationRoot, 'pytest')}`,
  ]

  process.stdout.write(`\n=== Python ${name} suite: ${SUITES[name]} ===\n`)
  let status = 1
  try {
    const result = spawnSync(python, args, {
      cwd: REPO_ROOT,
      env: isolatedEnvironment(isolationRoot),
      stdio: 'inherit',
    })
    status = result.status ?? 1
  } finally {
    const resolvedRoot = resolve(isolationRoot)
    const resolvedParent = resolve(isolationParent)
    if (
      dirname(resolvedRoot) !== resolvedParent ||
      !basename(resolvedRoot).startsWith(isolationPrefix)
    ) {
      throw new Error('Refusing to clean an unexpected Python test isolation path.')
    }
    rmSync(resolvedRoot, { recursive: true, force: true })
  }
  return status
}

function main() {
  const selection = process.argv[2] || 'all'
  const suites = selectedSuites(selection)
  const before = gitStatus()
  const results = suites.map(runSuite)
  const after = gitStatus()

  if (after !== before) {
    process.stderr.write(
      '\nPython tests changed the repository worktree. Persistent test writes are prohibited.\n',
    )
    return 1
  }
  return aggregateExitCode(results)
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main()
}

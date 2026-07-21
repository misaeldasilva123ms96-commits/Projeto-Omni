import { mkdtempSync, mkdirSync, rmSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { basename, dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SUITES = Object.freeze({
  backend: 'backend/python/tests',
  runtime: 'tests',
})
const HOST_ENV_ALLOWLIST = Object.freeze([
  'CI',
  'COLORTERM',
  'COMSPEC',
  'FORCE_COLOR',
  'GITHUB_ACTIONS',
  'LANG',
  'LC_ALL',
  'NO_COLOR',
  'NUMBER_OF_PROCESSORS',
  'PATH',
  'PATHEXT',
  'PROCESSOR_ARCHITECTURE',
  'PYTHONIOENCODING',
  'PYTHONUTF8',
  'RUNNER_OS',
  'SYSTEMROOT',
  'TERM',
  'WINDIR',
])
const COVERAGE_TARGETS = Object.freeze([
  'backend/python/brain/runtime/language',
  'backend/python/brain/runtime/control',
  'backend/python/brain/runtime/observability',
  'backend/python/brain/runtime/orchestrator_services',
  'backend/python/brain/runtime/sandbox',
])

export function aggregateExitCode(results) {
  return results.every((result) => result === 0) ? 0 : 1
}

export function selectedSuites(selection) {
  if (selection === 'all' || selection === 'coverage') return ['backend', 'runtime']
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

export function isolatedEnvironment(root) {
  const env = {}
  for (const key of HOST_ENV_ALLOWLIST) {
    const value = process.env[key]
    if (value !== undefined) env[key] = value
  }

  const directoryRoots = {
    OMNI_MEMORY_ROOT: join(root, 'memory'),
    OMNI_MEMORY_DIR: join(root, 'memory'),
    OMNI_CACHE_ROOT: join(root, 'cache'),
    OMNI_ARTIFACT_ROOT: join(root, 'artifacts'),
    OMNI_LOG_ROOT: join(root, 'logs'),
    OMNI_DATABASE_ROOT: join(root, 'databases'),
    OMNI_CREDENTIAL_ROOT: join(root, 'credentials'),
    OMNI_PROVIDER_STATE_ROOT: join(root, 'providers'),
    OMNI_RUNTIME_SESSION_ROOT: join(root, 'sessions'),
    OMNI_UPLOAD_ROOT: join(root, 'uploads'),
  }
  const filePaths = {
    OMNI_MEMORY_JSON_PATH: join(root, 'memory', 'memory.json'),
    OMNI_JSONL_MEMORY_PATH: join(root, 'memory', 'audit.jsonl'),
    OMNI_SQLITE_MEMORY_PATH: join(root, 'memory', 'memory.sqlite'),
  }
  const home = join(root, 'home')
  const temp = join(root, 'tmp')
  const xdg = {
    XDG_CONFIG_HOME: join(home, '.config'),
    XDG_CACHE_HOME: join(home, '.cache'),
    XDG_DATA_HOME: join(home, '.local', 'share'),
    XDG_STATE_HOME: join(home, '.local', 'state'),
  }
  for (const path of [
    ...Object.values(directoryRoots),
    ...Object.values(xdg),
    home,
    temp,
  ]) {
    mkdirSync(path, { recursive: true })
  }

  return {
    ...env,
    ...directoryRoots,
    ...filePaths,
    OMNI_BASE_DIR: REPO_ROOT,
    OMNI_PYTHON_BASE_DIR: join(REPO_ROOT, 'backend', 'python'),
    OMNI_PYTHON_ENTRY: join(REPO_ROOT, 'backend', 'python', 'main.py'),
    OMNI_WORKSPACE_ROOT: REPO_ROOT,
    OMNI_RUNTIME_MODE: 'live',
    OMNI_TEST_MODE: 'true',
    OMNI_ENABLE_SQLITE_MEMORY: 'false',
    HOME: home,
    USERPROFILE: home,
    TEMP: temp,
    TMP: temp,
    TMPDIR: temp,
    ...xdg,
    GIT_CONFIG_GLOBAL: process.platform === 'win32' ? 'NUL' : '/dev/null',
    PYTHONDONTWRITEBYTECODE: '1',
  }
}

function validatedIsolationRoot(isolationRoot, isolationParent, isolationPrefix) {
  const resolvedRoot = resolve(isolationRoot)
  const resolvedParent = resolve(isolationParent)
  if (
    dirname(resolvedRoot) !== resolvedParent ||
    !basename(resolvedRoot).startsWith(isolationPrefix)
  ) {
    throw new Error('Refusing to use an unexpected Python test isolation path.')
  }
  return resolvedRoot
}

function pythonCommand() {
  return process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3')
}

function runSuite(name, coverage = null) {
  const isolationParent = dirname(REPO_ROOT)
  mkdirSync(isolationParent, { recursive: true })
  const isolationPrefix = `.omni-python-${name}-${process.pid}-`
  const isolationRoot = mkdtempSync(join(isolationParent, isolationPrefix))
  const resolvedRoot = validatedIsolationRoot(isolationRoot, isolationParent, isolationPrefix)
  const python = pythonCommand()
  const args = [
    '-m',
    'pytest',
    '-q',
    SUITES[name],
    `--basetemp=${join(isolationRoot, 'pytest')}`,
  ]
  const env = isolatedEnvironment(isolationRoot)
  if (coverage) {
    env.COVERAGE_FILE = coverage.file
    args.push('--cov-config=.coveragerc', '--cov-report=', '--cov-fail-under=0')
    for (const target of COVERAGE_TARGETS) args.push(`--cov=${target}`)
    if (coverage.append) args.push('--cov-append')
  }

  process.stdout.write(`\n=== Python ${name} suite: ${SUITES[name]} ===\n`)
  let status = 1
  try {
    const result = spawnSync(python, args, {
      cwd: REPO_ROOT,
      env,
      stdio: 'inherit',
    })
    status = result.status ?? 1
  } catch (error) {
    process.stderr.write(
      `Python ${name} suite could not start (${error?.name || 'Error'}).\n`,
    )
    status = 1
  } finally {
    try {
      rmSync(resolvedRoot, { recursive: true, force: true })
    } catch (error) {
      process.stderr.write(
        `Python ${name} isolation cleanup failed (${error?.name || 'Error'}).\n`,
      )
      status = 1
    }
  }
  return status
}

function runCoverageReport(coverageDir, coverageFile) {
  const python = pythonCommand()
  const reportEnv = isolatedEnvironment(coverageDir)
  reportEnv.COVERAGE_FILE = coverageFile
  const report = spawnSync(
    python,
    ['-m', 'coverage', 'report', '--rcfile=.coveragerc', '--fail-under=40'],
    { cwd: REPO_ROOT, env: reportEnv, stdio: 'inherit' },
  )
  const xml = spawnSync(
    python,
    [
      '-m',
      'coverage',
      'xml',
      '--rcfile=.coveragerc',
      '-o',
      join(coverageDir, 'coverage.xml'),
    ],
    { cwd: REPO_ROOT, env: reportEnv, stdio: 'inherit' },
  )
  return aggregateExitCode([report.status ?? 1, xml.status ?? 1])
}

function main() {
  const selection = process.argv[2] || 'all'
  const suites = selectedSuites(selection)
  const coverageEnabled = selection === 'coverage'
  const before = gitStatus()
  let coverage = null
  if (coverageEnabled) {
    const coverageDir = join(REPO_ROOT, '.tmp', 'python-coverage')
    rmSync(coverageDir, { recursive: true, force: true })
    mkdirSync(coverageDir, { recursive: true })
    coverage = { dir: coverageDir, file: join(coverageDir, '.coverage') }
  }
  const results = suites.map((suite, index) =>
    runSuite(
      suite,
      coverage ? { file: coverage.file, append: index > 0 } : null,
    ),
  )
  if (coverage) results.push(runCoverageReport(coverage.dir, coverage.file))
  const after = gitStatus()

  if (after !== before) {
    process.stderr.write(
      '\nPython tests changed the repository worktree. Persistent test writes are prohibited.\n',
    )
    process.stderr.write(`Status before:\n${before || '(clean)\n'}`)
    process.stderr.write(`Status after:\n${after || '(clean)\n'}`)
    return 1
  }
  return aggregateExitCode(results)
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = main()
}

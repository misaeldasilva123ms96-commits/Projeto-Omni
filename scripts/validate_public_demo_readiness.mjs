import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

const requiredFiles = [
  'Dockerfile.demo',
  'docker-compose.demo.yml',
  '.dockerignore',
  '.env.example',
  'docs/deploy/PUBLIC_DEMO_CONTAINER.md',
  'docs/security/secrets-policy.md',
  'docs/training/TRAINING_READINESS.md',
  'tests/security/security-regression-suite.mjs',
  'package.json',
]

const requiredDemoEnv = [
  ['OMNI_PUBLIC_DEMO_MODE', 'true'],
  ['OMINI_PUBLIC_DEMO_MODE', 'true'],
  ['OMNI_ALLOW_SHELL_TOOLS', 'false'],
  ['OMINI_ALLOW_SHELL_TOOLS', 'false'],
  ['OMNI_DEBUG_INTERNAL_ERRORS', 'false'],
  ['OMINI_DEBUG_INTERNAL_ERRORS', 'false'],
  ['OMNI_RATE_LIMIT_ENABLED', 'true'],
  ['OMNI_RATE_LIMIT_PER_MINUTE', '30'],
  ['OMNI_MAX_MESSAGE_CHARS', '8000'],
  ['OMNI_MAX_BODY_BYTES', '65536'],
  ['OMNI_INTENT_CLASSIFIER', 'regex'],
  ['OMNI_MATCHER_MODE', 'enabled'],
  ['OMNI_PYTHON_MODE', 'subprocess'],
  ['OMNI_NODE_MODE', 'subprocess'],
]

const dockerignoreEntries = [
  '.git',
  '.env',
  '.env.*',
  '!.env.example',
  'node_modules',
  'frontend/node_modules',
  'backend/rust/target',
  'logs',
  'runtime_logs',
  'learning_logs',
  'storage/local',
  '*.trace.json',
  '*.debug.json',
  '__pycache__',
  '.pytest_cache',
]

const secretPatterns = [
  /\bsk-(proj-)?[A-Za-z0-9_-]{12,}/,
  /\bsk-ant-[A-Za-z0-9_-]{12,}/,
  /\bsk-groq-[A-Za-z0-9_-]{12,}/,
  /\bBearer\s+[A-Za-z0-9._-]{16,}/i,
  /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/,
  /\bghp_[A-Za-z0-9_]{12,}/,
  /\bxox[baprs]-[A-Za-z0-9-]{12,}/,
]

function readText(relativePath) {
  return fs.readFileSync(path.join(projectRoot, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

function fileExists(relativePath) {
  return fs.existsSync(path.join(projectRoot, relativePath))
}

function validateRequiredFiles() {
  for (const relativePath of requiredFiles) {
    assert(fileExists(relativePath), `missing required file: ${relativePath}`)
  }
}

function validatePackageScripts() {
  const packageJson = JSON.parse(readText('package.json'))
  assert(packageJson.scripts?.['test:security'], 'package.json missing test:security script')
  assert(packageJson.scripts?.['validate:public-demo'], 'package.json missing validate:public-demo script')
}

function validateDemoEnv(text, source) {
  for (const [key, expectedValue] of requiredDemoEnv) {
    const pattern = new RegExp(`${key}\\s*[:=]\\s*["']?${expectedValue}["']?`)
    assert(pattern.test(text), `${source} missing ${key}=${expectedValue}`)
  }
}

function validateDockerfile() {
  const dockerfile = readText('Dockerfile.demo')
  validateDemoEnv(dockerfile, 'Dockerfile.demo')
  assert(/\bUSER\s+omni\b/.test(dockerfile), 'Dockerfile.demo must run as non-root user omni')
  assert(!/SUPABASE_SERVICE_ROLE_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GROQ_API_KEY/.test(dockerfile), 'Dockerfile.demo must not bake provider or Supabase secrets')
}

function validateCompose() {
  const compose = readText('docker-compose.demo.yml')
  validateDemoEnv(compose, 'docker-compose.demo.yml')
  assert(/read_only:\s*true/.test(compose), 'compose must use read_only: true')
  assert(/cap_drop:\s*\r?\n\s*-\s*ALL/.test(compose), 'compose must drop all capabilities')
  assert(/no-new-privileges:true/.test(compose), 'compose must set no-new-privileges')
  assert(!/privileged:\s*true/.test(compose), 'compose must not use privileged mode')
  assert(!/docker\.sock/.test(compose), 'compose must not mount docker.sock')
  assert(!/SUPABASE_SERVICE_ROLE_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GROQ_API_KEY/.test(compose), 'compose must not contain raw secret env names')
}

function validateDockerignore() {
  const dockerignore = readText('.dockerignore')
  for (const entry of dockerignoreEntries) {
    assert(dockerignore.split(/\r?\n/).includes(entry), `.dockerignore missing ${entry}`)
  }
}

function validateNoObviousSecrets() {
  const files = [
    '.env.example',
    'Dockerfile.demo',
    'docker-compose.demo.yml',
    'docs/deploy/PUBLIC_DEMO_CONTAINER.md',
  ]
  for (const relativePath of files) {
    const text = readText(relativePath)
    for (const pattern of secretPatterns) {
      assert(!pattern.test(text), `${relativePath} contains real-looking secret pattern`)
    }
  }
}

function main() {
  validateRequiredFiles()
  validatePackageScripts()
  validateDockerfile()
  validateCompose()
  validateDockerignore()
  validateNoObviousSecrets()
  process.stdout.write(JSON.stringify({
    ok: true,
    checked_files: requiredFiles.length,
    demo_env_checked: requiredDemoEnv.map(([key]) => key),
    dockerignore_entries_checked: dockerignoreEntries.length,
  }, null, 2))
  process.stdout.write('\n')
}

main()

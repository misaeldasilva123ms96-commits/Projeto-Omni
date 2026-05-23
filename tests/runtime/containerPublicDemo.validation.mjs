import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

function read(relativePath) {
  return fs.readFileSync(path.join(projectRoot, relativePath), 'utf8');
}

function assertContains(text, expected, label) {
  assert.ok(text.includes(expected), `${label} missing ${expected}`);
}

const cargoToml = read('backend/rust/Cargo.toml');
assert.match(cargoToml, /name\s*=\s*"omini-api"/, 'Cargo.toml must define omini-api package');

const dockerfile = read('Dockerfile.demo');
const compose = read('docker-compose.demo.yml');
const dockerignore = read('.dockerignore');
const publicDoc = read('docs/deploy/PUBLIC_DEMO_CONTAINER.md');
const auditDoc = read('docs/audit/PHASE_6_CONTAINER_PUBLIC_DEMO.md');

for (const [key, value] of [
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
]) {
  assertContains(dockerfile, `${key}=${value}`, 'Dockerfile.demo env');
  assertContains(compose, `${key}: "${value}"`, 'docker-compose.demo.yml env');
}

assertContains(dockerfile, 'cargo build --release --bin omini-api', 'verified Rust binary build');
assertContains(dockerfile, 'COPY --from=rust-builder /build/backend/rust/target/release/omini-api', 'verified Rust binary copy');
assertContains(dockerfile, 'npm ci --omit=dev', 'npm lockfile install');
assertContains(dockerfile, 'USER omni', 'non-root runtime user');
assertContains(dockerfile, 'EXPOSE 3001', 'Rust API port');

for (const dir of ['backend/python', 'js-runner', 'src', 'core', 'features', 'platform', 'runtime', 'storage', 'configs', 'observability', 'contract']) {
  assertContains(dockerfile, `COPY --chown=omni:omni ${dir} `, `runtime dir ${dir}`);
}

assert.equal(/\bprivileged\s*:\s*true\b/i.test(compose), false, 'compose must not enable privileged mode');
assert.equal(compose.includes('/var/run/docker.sock'), false, 'compose must not mount docker.sock');
assert.equal(compose.includes('cap_drop:'), true, 'compose must drop capabilities');
assert.equal(compose.includes('no-new-privileges:true'), true, 'compose must set no-new-privileges');
assert.equal(compose.includes('read_only: true'), true, 'compose must use read-only rootfs');
assert.equal(compose.includes('/tmp:size='), true, 'compose must provide tmpfs /tmp');

for (const pattern of ['.git', '.env', '.env.*', '!.env.example', 'node_modules', 'frontend/node_modules', 'backend/rust/target', 'target', 'dist', 'build', 'logs', '.logs', 'runtime_logs', 'learning_logs', 'storage/local', '*.trace.json', '*.debug.json', '__pycache__', '.pytest_cache']) {
  assertContains(dockerignore, pattern, '.dockerignore');
}

for (const text of [dockerfile, compose, publicDoc, auditDoc]) {
  for (const forbidden of ['sk-proj-', 'sk-', 'Bearer ', 'ghp_', 'xoxb-', 'SUPABASE_SERVICE_ROLE_KEY=', 'OPENAI_API_KEY=']) {
    assert.equal(text.includes(forbidden), false, `forbidden secret-like value found: ${forbidden}`);
  }
}

console.log('container public demo validation: ok');

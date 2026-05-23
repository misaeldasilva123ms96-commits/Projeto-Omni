import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import http from 'node:http'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')
const service = require('../../js-runner/queryEngineService.js')

function request(port, method, pathname, body, contentType = 'application/json') {
  return new Promise((resolve, reject) => {
    const payload = body === undefined ? null : Buffer.from(JSON.stringify(body), 'utf8')
    const req = http.request({
      hostname: '127.0.0.1',
      port,
      path: pathname,
      method,
      headers: payload ? {
        'content-type': contentType,
        'content-length': String(payload.length),
      } : {},
    }, (res) => {
      const chunks = []
      res.on('data', (chunk) => chunks.push(chunk))
      res.on('end', () => {
        resolve({
          status: res.statusCode,
          body: JSON.parse(Buffer.concat(chunks).toString('utf8')),
        })
      })
    })
    req.on('error', reject)
    if (payload) req.write(payload)
    req.end()
  })
}

function serialized(value) {
  return JSON.stringify(value)
}

assert.deepEqual(service.getServiceConfig(), { host: '127.0.0.1', port: 7020 })
process.env.OMINI_NODE_SERVICE_HOST = '127.0.0.2'
process.env.OMINI_NODE_SERVICE_PORT = '7021'
assert.deepEqual(service.getServiceConfig(), { host: '127.0.0.2', port: 7021 })
process.env.OMNI_NODE_SERVICE_HOST = '127.0.0.3'
process.env.OMNI_NODE_SERVICE_PORT = '7022'
assert.deepEqual(service.getServiceConfig(), { host: '127.0.0.3', port: 7022 })
delete process.env.OMNI_NODE_SERVICE_HOST
delete process.env.OMNI_NODE_SERVICE_PORT
delete process.env.OMINI_NODE_SERVICE_HOST
delete process.env.OMINI_NODE_SERVICE_PORT

assert.deepEqual(service.healthPayload(), {
  ok: true,
  service: 'node-query-engine',
  mode: 'service',
})
const readiness = service.readinessPayload()
assert.equal(readiness.ok, true)
assert.equal(readiness.checks.query_engine_runner_importable, true)
assert.equal(serialized(readiness).includes('env'), false)

const fakeRuntime = {
  async tryRunExistingQueryEngineDetailed(payload) {
    assert.equal(payload.message, 'ola')
    assert.equal(payload.session.session_id, 'sess-1')
    assert.equal(payload.session.request_id, 'req-1')
    return {
      result: {
        response: 'resposta ok',
        runtime_truth: {
          runtime_mode: 'TOOL_EXECUTED',
          tool_status: 'succeeded',
          governance_status: 'allowed',
        },
        error_public_code: 'RULE_BASED_INTENT_USED',
        error_public_message: 'Intent was classified by deterministic rules.',
        severity: 'info',
        retryable: false,
        internal_error_redacted: true,
        governance_audit: {
          allowed: true,
          category: 'read_safe',
          stack: 'hidden',
        },
        execution_request: { actions: [{ command: 'rm -rf /' }] },
        raw_payload: { token: 'hidden' },
      },
    }
  },
  sanitizeForUser(value) {
    return value
  },
}

const [okStatus, okPayload] = await service.handleRunPayload({
  message: 'ola',
  session_id: 'sess-1',
  request_id: 'req-1',
  metadata: { source: 'test' },
  runtime_context: {},
}, fakeRuntime)
assert.equal(okStatus, 200)
assert.equal(okPayload.response, 'resposta ok')
assert.equal(okPayload.runtime_truth.runtime_mode, 'TOOL_EXECUTED')
assert.equal(okPayload.runtime_truth.tool_status, 'succeeded')
assert.equal(okPayload.runtime_truth.governance_status, 'allowed')
assert.equal(okPayload.error_public_code, 'RULE_BASED_INTENT_USED')
assert.equal(okPayload.severity, 'info')
assert.equal(okPayload.retryable, false)
assert.equal(okPayload.service, 'node-query-engine')
assert.equal(okPayload.mode, 'service')
assert.equal(serialized(okPayload).includes('execution_request'), false)
assert.equal(serialized(okPayload).includes('raw_payload'), false)
assert.equal(serialized(okPayload).includes('rm -rf'), false)
assert.equal(serialized(okPayload).includes('hidden'), false)

const [badStatus, badPayload] = await service.handleRunPayload({ message: '' }, fakeRuntime)
assert.equal(badStatus, 400)
assert.equal(badPayload.error_public_code, 'INPUT_VALIDATION_FAILED')
assert.equal(badPayload.internal_error_redacted, true)

const failingRuntime = {
  async tryRunExistingQueryEngineDetailed() {
    throw new Error('/home/render/.env sk-proj-secret stack')
  },
  sanitizeForUser(value) {
    return value
  },
}
const [failStatus, failPayload] = await service.handleRunPayload({ message: 'ola' }, failingRuntime)
assert.equal(failStatus, 500)
assert.equal(failPayload.error_public_code, 'NODE_RUNNER_FAILED')
assert.equal(failPayload.internal_error_redacted, true)
assert.equal(serialized(failPayload).includes('/home/render'), false)
assert.equal(serialized(failPayload).includes('sk-proj'), false)
assert.equal(serialized(failPayload).includes('stack'), false)

const server = service.createServer()
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
const port = server.address().port
try {
  const health = await request(port, 'GET', '/internal/query-engine/health')
  assert.equal(health.status, 200)
  assert.equal(health.body.service, 'node-query-engine')

  const ready = await request(port, 'GET', '/internal/query-engine/readiness')
  assert.equal(ready.status, 200)
  assert.equal(ready.body.checks.public_sanitizer, true)

  const invalidType = await request(port, 'POST', '/internal/query-engine/run', { message: 'ola' }, 'text/plain')
  assert.equal(invalidType.status, 415)
  assert.equal(invalidType.body.error_public_code, 'INVALID_CONTENT_TYPE')
} finally {
  await new Promise((resolve) => server.close(resolve))
}

const cli = spawnSync(
  process.execPath,
  ['js-runner/queryEngineRunner.js'],
  {
    cwd: projectRoot,
    input: JSON.stringify({ message: 'ola', memory: {}, history: [], summary: '', capabilities: [], session: {} }),
    encoding: 'utf8',
    timeout: 30_000,
  },
)
assert.equal(cli.status, 0)
const cliPayload = JSON.parse(cli.stdout)
assert.equal(typeof cliPayload.response, 'string')
assert.ok(cliPayload.response.trim().length > 0)
assert.equal(serialized(cliPayload).toLowerCase().includes('traceback'), false)

console.log('node query engine service: checks passed')

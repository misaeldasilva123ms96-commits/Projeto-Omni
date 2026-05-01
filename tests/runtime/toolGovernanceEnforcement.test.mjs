import assert from 'node:assert/strict'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const {
  buildGovernanceBlockedResult,
  evaluateToolGovernance,
} = require('../../runtime/tooling/toolGovernance.js')

function withEnv(values, fn) {
  const previous = {}
  for (const key of Object.keys(values)) {
    previous[key] = process.env[key]
    process.env[key] = values[key]
  }
  try {
    fn()
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key]
      else process.env[key] = value
    }
  }
}

function testCategoriesAndBlocks() {
  assert.equal(evaluateToolGovernance({ selected_tool: 'git_status' }).allowed, true)
  assert.equal(evaluateToolGovernance({ selected_tool: 'git_diff' }).category, 'read_safe')

  const readSensitive = evaluateToolGovernance({ selected_tool: 'read_file', tool_arguments: {} })
  assert.equal(readSensitive.allowed, false)
  assert.equal(readSensitive.error_public_code, 'TOOL_APPROVAL_REQUIRED')

  const write = evaluateToolGovernance({ selected_tool: 'write_file', tool_arguments: { path: 'x' } })
  assert.equal(write.allowed, false)
  assert.equal(write.category, 'write')

  assert.equal(evaluateToolGovernance({ selected_tool: 'git_reset' }).category, 'destructive')
  assert.equal(evaluateToolGovernance({ selected_tool: 'git_reset' }).allowed, false)
  assert.equal(evaluateToolGovernance({ selected_tool: 'git_clean' }).allowed, false)
  assert.equal(evaluateToolGovernance({ selected_tool: 'git_commit' }).category, 'git_sensitive')
  assert.equal(evaluateToolGovernance({ selected_tool: 'git_push' }).allowed, false)
  assert.equal(evaluateToolGovernance({ selected_tool: 'web_request' }).category, 'network')
}

function testPublicDemoPrecedence() {
  withEnv({ ALLOW_SHELL: 'true', OMNI_PUBLIC_DEMO_MODE: 'true' }, () => {
    const decision = evaluateToolGovernance({ selected_tool: 'shell_command' })
    assert.equal(decision.allowed, false)
    assert.equal(decision.error_public_code, 'TOOL_BLOCKED_PUBLIC_DEMO')
    assert.equal(decision.governance_audit.public_demo_blocked, true)
  })
}

function testBlockedResultPublicSafe() {
  const decision = evaluateToolGovernance({ selected_tool: 'write_file', tool_arguments: { path: 'secret.txt' } })
  const result = buildGovernanceBlockedResult({ selected_tool: 'write_file' }, decision)
  assert.equal(result.ok, false)
  assert.equal(result.tool_status, 'blocked')
  assert.equal(result.internal_error_redacted, true)
  assert.equal(result.tool_execution.tool_denied, true)

  const serialized = JSON.stringify(result).toLowerCase()
  for (const forbidden of ['stack', 'traceback', 'env', 'token', 'stdout', 'stderr', 'raw_payload']) {
    assert.equal(serialized.includes(forbidden), false)
  }
}

testCategoriesAndBlocks()
testPublicDemoPrecedence()
testBlockedResultPublicSafe()
console.log('tool governance enforcement: js checks passed')

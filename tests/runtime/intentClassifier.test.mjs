import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const {
  QueryEngineAuthority,
  classifyIntent,
  inferIntent,
  inferIntentWithSource,
  resolveIntentClassifierMode,
  resolveMatcherMode,
} = require('../../core/brain/queryEngineAuthority.js')

const ORIGINAL_ENV = { ...process.env }

function resetEnv() {
  for (const key of [
    'OMNI_INTENT_CLASSIFIER',
    'OMINI_INTENT_CLASSIFIER',
    'OMNI_MATCHER_MODE',
    'OMINI_MATCHER_MODE',
    'OMINI_SKIP_CONVERSATIONAL_MATCHERS',
  ]) {
    delete process.env[key]
  }
}

function restoreEnv() {
  process.env = { ...ORIGINAL_ENV }
}

function testDefaultClassifierMode() {
  resetEnv()
  assert.equal(resolveIntentClassifierMode(), 'regex')
  assert.equal(resolveMatcherMode(), 'enabled')
}

function testLegacyAliases() {
  resetEnv()
  process.env.OMINI_INTENT_CLASSIFIER = 'hybrid'
  process.env.OMINI_MATCHER_MODE = 'labeled_only'
  assert.equal(resolveIntentClassifierMode(), 'hybrid')
  assert.equal(resolveMatcherMode(), 'labeled_only')

  process.env.OMNI_INTENT_CLASSIFIER = 'regex'
  process.env.OMNI_MATCHER_MODE = 'disabled'
  assert.equal(resolveIntentClassifierMode(), 'regex')
  assert.equal(resolveMatcherMode(), 'disabled')
}

function testRegexCompatibility() {
  resetEnv()
  const message = 'analise o arquivo package.json'
  const classified = classifyIntent(message)
  assert.equal(inferIntent.length, 1)
  assert.equal(classified.intent, inferIntent(message))
  assert.equal(classified.intent_source, 'rule_based')
  assert.equal(classified.classifier_version, 'regex_v1')

  const wrapped = inferIntentWithSource(message)
  assert.equal(wrapped.intent, 'execution')
  assert.equal(wrapped.intent_source, 'rule_based')
  assert.equal(wrapped.classifier_mode, 'regex')
}

async function testMatcherEnabledIsLabeled() {
  resetEnv()
  const engine = new QueryEngineAuthority()
  const result = await engine.submitMessage({
    message: 'oi',
    memoryContext: {},
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'intent-classifier-matcher-enabled' },
    cwd: process.cwd(),
  })

  assert.equal(result.runtime_truth.matcher_used, true)
  assert.equal(result.runtime_truth.classifier_mode, 'regex')
  assert.equal(result.runtime_truth.llm_provider_attempted, false)
}

async function testMatcherDisabledDoesNotBreakFallback() {
  resetEnv()
  process.env.OMNI_MATCHER_MODE = 'disabled'
  const engine = new QueryEngineAuthority()
  const result = await engine.submitMessage({
    message: 'oi',
    memoryContext: {},
    history: [],
    summary: '',
    capabilities: [],
    session: { session_id: 'intent-classifier-matcher-disabled' },
    cwd: process.cwd(),
  })

  assert.ok(typeof result.response === 'string')
  assert.notEqual(result.runtime_truth?.matcher_used, true)
}

function testLowConfidenceDoesNotTriggerTools() {
  resetEnv()
  const classified = classifyIntent('uma frase ambigua sem pedido operacional claro')
  assert.equal(classified.intent, 'conversation')
  assert.ok(classified.confidence < 0.6)
  assert.equal(classified.provider_attempted, false)
  assert.equal(classified.provider_succeeded, false)
}

function testLlmModeFailsClosed() {
  resetEnv()
  process.env.OMNI_INTENT_CLASSIFIER = 'llm'
  const classified = classifyIntent('debug do runtime')
  assert.equal(classified.classifier_mode, 'llm')
  assert.equal(classified.intent_source, 'rule_based')
  assert.equal(classified.provider_attempted, false)
  assert.equal(classified.provider_succeeded, false)
  assert.match(classified.classifier_version, /fallback/)
}

function testHybridRuntimeTruthLabelsSource() {
  resetEnv()
  process.env.OMNI_INTENT_CLASSIFIER = 'hybrid'
  const classified = classifyIntent('corrija os testes')
  assert.equal(classified.classifier_mode, 'hybrid')
  assert.equal(classified.intent_source, 'hybrid')
  assert.equal(classified.provider_attempted, false)
}

function testEvalHarness() {
  resetEnv()
  const result = spawnSync(
    process.execPath,
    ['scripts/evaluate_intent_classifier.mjs', '--mode=regex', '--input=data/evals/intent_eval.jsonl'],
    { cwd: process.cwd(), encoding: 'utf8' },
  )

  assert.equal(result.status, 0, result.stderr)
  const metrics = JSON.parse(result.stdout)
  assert.equal(metrics.mode, 'regex')
  assert.ok(metrics.total >= 10)
  assert.equal(metrics.provider_usage_rate, 0)
  assert.ok(Number.isFinite(metrics.accuracy))
}

try {
  testDefaultClassifierMode()
  testLegacyAliases()
  testRegexCompatibility()
  await testMatcherEnabledIsLabeled()
  await testMatcherDisabledDoesNotBreakFallback()
  testLowConfidenceDoesNotTriggerTools()
  testLlmModeFailsClosed()
  testHybridRuntimeTruthLabelsSource()
  testEvalHarness()
  console.log('intent classifier: js checks passed')
} finally {
  restoreEnv()
}

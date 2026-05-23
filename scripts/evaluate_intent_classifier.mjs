import fs from 'node:fs'
import { createRequire } from 'node:module'
import path from 'node:path'

const require = createRequire(import.meta.url)
const { classifyIntent } = require('../core/brain/queryEngineAuthority.js')

function parseArgs(argv) {
  const options = {
    mode: 'regex',
    input: 'data/evals/intent_eval.jsonl',
  }
  for (const arg of argv) {
    if (arg.startsWith('--mode=')) {
      options.mode = arg.slice('--mode='.length)
    } else if (arg.startsWith('--input=')) {
      options.input = arg.slice('--input='.length)
    }
  }
  return options
}

function readJsonl(filePath) {
  const absolutePath = path.resolve(process.cwd(), filePath)
  const content = fs.readFileSync(absolutePath, 'utf8')
  return content
    .split(/\r?\n/)
    .filter(line => line.trim())
    .map((line, index) => {
      try {
        return JSON.parse(line)
      } catch (err) {
        throw new Error(`Invalid JSONL at line ${index + 1}`)
      }
    })
}

function expectedIntentForCase(item) {
  return item?.expected?.intent || item?.expected_intent || ''
}

function safeRate(value, total) {
  if (!total) return 0
  return Number((value / total).toFixed(4))
}

function evaluate({ mode, input }) {
  process.env.OMNI_INTENT_CLASSIFIER = mode
  delete process.env.OMINI_INTENT_CLASSIFIER

  const cases = readJsonl(input)
  let evaluated = 0
  let correct = 0
  let fallbackCount = 0
  let matcherUsageCount = 0
  let providerUsageCount = 0
  let lowConfidenceCount = 0
  const byIntent = {}

  for (const item of cases) {
    const expectedIntent = expectedIntentForCase(item)
    const classified = classifyIntent(item.input || item.message || '')
    const actualIntent = classified.intent
    if (expectedIntent) {
      evaluated += 1
      if (actualIntent === expectedIntent) {
        correct += 1
      }
    }
    if (!byIntent[actualIntent]) {
      byIntent[actualIntent] = { count: 0, correct: 0 }
    }
    byIntent[actualIntent].count += 1
    if (expectedIntent && actualIntent === expectedIntent) {
      byIntent[actualIntent].correct += 1
    }
    if (String(classified.classifier_version || '').includes('fallback')) {
      fallbackCount += 1
    }
    if (classified.matcher_used) {
      matcherUsageCount += 1
    }
    if (classified.provider_attempted) {
      providerUsageCount += 1
    }
    if (Number(classified.confidence || 0) < 0.6) {
      lowConfidenceCount += 1
    }
  }

  return {
    mode,
    input,
    total: cases.length,
    evaluated,
    correct,
    accuracy: safeRate(correct, evaluated),
    fallback_rate: safeRate(fallbackCount, cases.length),
    matcher_usage_rate: safeRate(matcherUsageCount, cases.length),
    provider_usage_rate: safeRate(providerUsageCount, cases.length),
    low_confidence_rate: safeRate(lowConfidenceCount, cases.length),
    by_intent: byIntent,
  }
}

const options = parseArgs(process.argv.slice(2))
const metrics = evaluate(options)
process.stdout.write(`${JSON.stringify(metrics, null, 2)}\n`)

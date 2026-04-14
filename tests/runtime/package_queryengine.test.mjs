import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const projectRoot = process.cwd()
const engineAdoptionPath = path.join(projectRoot, '.logs', 'fusion-runtime', 'engine_adoption.json')
const packagedModulePath = path.join(projectRoot, 'dist', 'QueryEngine.js')
const packagedModulePackageJsonPath = path.join(projectRoot, 'dist', 'package.json')
const packageModule = await import(pathToFileURL(path.join(projectRoot, 'scripts', 'package-queryengine.mjs')).href)

const packaged = packageModule.packageQueryEngine()
assert.equal(packaged.ok, true)

assert.equal(fs.existsSync(packagedModulePath), true, 'Artefato empacotado do QueryEngine deve existir')
assert.equal(fs.existsSync(packagedModulePackageJsonPath), true, 'package.json do artefato empacotado deve existir')

const packagedModule = await import(pathToFileURL(packagedModulePath).href)
assert.equal(typeof packagedModule.runQueryEngine, 'function')

const response = await packagedModule.runQueryEngine({
  message: 'explique como funciona memoria de contexto',
  memoryContext: { user: { nome: 'Misael', preferencias: ['tecnologia'] } },
  history: [],
  summary: '',
  capabilities: [],
  session: { session_id: 'package-queryengine-test' },
})

assert.equal(typeof response.response, 'string')
assert.ok(response.response.length > 0)
assert.equal(typeof response.confidence, 'number')
assert.equal(response.metadata?.engine_mode, 'packaged_upstream')
assert.equal(response.metadata?.engine_reason, 'dist_candidate_selected')

const promotedResponse = await packagedModule.runQueryEngine({
  message: 'explique o contexto da sessao atual',
  memoryContext: { user: {} },
  history: [],
  summary: '',
  capabilities: [],
  session: {
    session_id: 'package-queryengine-promoted-test',
    executor_bridge: 'python-rust',
  },
})

assert.equal(promotedResponse.metadata?.engine_mode, 'packaged_upstream')
assert.equal(promotedResponse.metadata?.engine_reason, 'dist_candidate_selected')
assert.equal(promotedResponse.metadata?.promoted_scenario, 'executor_bridge_light_request')
assert.equal(promotedResponse.metadata?.promotion_phase, '27')

const heavyResponse = await packagedModule.runQueryEngine({
  message: 'analise o repositorio e corrija os testes com seguranca',
  memoryContext: { user: {} },
  history: [],
  summary: '',
  capabilities: [],
  session: {
    session_id: 'package-queryengine-heavy-test',
    runtime_mode: 'python-rust-cargo',
    milestone_plan: { preexisting: true },
  },
})

assert.equal(heavyResponse.metadata?.engine_mode, 'authority_fallback')
assert.equal(heavyResponse.metadata?.engine_reason, 'fallback_policy_triggered')

fs.mkdirSync(path.dirname(engineAdoptionPath), { recursive: true })
fs.writeFileSync(
  engineAdoptionPath,
  JSON.stringify({
    scope: 'session',
    session_id: 'package-queryengine-promoted-test',
    engine_counters: {
      packaged_upstream: 1,
      authority_fallback: 3,
      fallback_by_reason: {
        heavy_execution_request: 0,
        packaged_import_failed: 3,
        fallback_policy_triggered: 0,
      },
    },
  }, null, 2),
)

const rollbackResponse = await packagedModule.runQueryEngine({
  message: 'explique o contexto da sessao atual',
  memoryContext: { user: {} },
  history: [],
  summary: '',
  capabilities: [],
  session: {
    session_id: 'package-queryengine-promoted-test',
    executor_bridge: 'python-rust',
  },
})

assert.equal(rollbackResponse.metadata?.engine_mode, 'authority_fallback')
assert.equal(rollbackResponse.metadata?.engine_reason, 'fallback_policy_triggered')
assert.equal(rollbackResponse.metadata?.promoted_scenario, 'executor_bridge_light_request')
assert.equal(rollbackResponse.metadata?.promotion_phase, '27')
assert.equal(rollbackResponse.metadata?.promotion_rollback_reason, 'packaged_import_failed_threshold_exceeded')

console.log('package queryengine tests: ok')

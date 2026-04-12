import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const projectRoot = process.cwd()
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

console.log('package queryengine tests: ok')

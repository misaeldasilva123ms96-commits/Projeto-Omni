import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const projectRoot = process.cwd()
const queryEnginePath = path.join(projectRoot, 'runtime', 'node', 'QueryEngine.ts')

function parseImports(source) {
  const matches = []
  const pattern = /import\s+(?:type\s+)?(?:.+?\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\)/g
  let match
  while ((match = pattern.exec(source))) {
    matches.push(match[1] || match[2])
  }
  return matches
}

function analyzeImportGraph() {
  const source = fs.readFileSync(queryEnginePath, 'utf8')
  const imports = parseImports(source)
  return imports.map(specifier => {
    if (specifier.startsWith('bun:')) {
      return { specifier, status: 'BROKEN', kind: 'runtime-only' }
    }
    if (specifier.startsWith('./') || specifier.startsWith('../')) {
      const resolved = path.resolve(path.dirname(queryEnginePath), specifier)
      const exists =
        fs.existsSync(resolved) ||
        fs.existsSync(`${resolved}.js`) ||
        fs.existsSync(`${resolved}.ts`) ||
        fs.existsSync(path.join(resolved, 'index.js')) ||
        fs.existsSync(path.join(resolved, 'index.ts'))
      return {
        specifier,
        status: exists ? 'OK' : 'BROKEN',
        kind: 'relative',
      }
    }
    if (specifier.startsWith('src/')) {
      return { specifier, status: 'BROKEN', kind: 'alias' }
    }
    return { specifier, status: 'EXPECTED_SERVER_DEPENDENCY', kind: 'package' }
  })
}

async function main() {
  assert.equal(fs.existsSync(queryEnginePath), true, 'QueryEngine.ts should exist in runtime/node')

  const importGraph = analyzeImportGraph()
  assert.ok(importGraph.length > 0, 'Import graph should not be empty')

  let importError = null
  try {
    const module = await import(pathToFileURL(queryEnginePath).href)
    assert.ok(module.QueryEngine, 'QueryEngine export should exist when import succeeds')
    const engine = new module.QueryEngine({})
    const result = engine ? 'initialized' : 'not-initialized'
    assert.ok(result)
  } catch (error) {
    importError = error
  }

  assert.ok(importError, 'Current standalone QueryEngine import should fail in a controlled way')
  assert.ok(
    String(importError.code || '').includes('ERR_') || /bun:|Cannot find module|unsupported/i.test(String(importError.message || '')),
    `Unexpected import error: ${String(importError?.message || importError)}`,
  )

  const bunDependency = importGraph.find(item => item.specifier === 'bun:bundle')
  assert.ok(bunDependency, 'Expected bun:bundle import to be detected')
  assert.equal(bunDependency.status, 'BROKEN')

  const brokenRelative = importGraph.find(item => item.kind === 'relative' && item.status === 'BROKEN')
  assert.ok(brokenRelative, 'Expected at least one broken relative import after the move')

  console.log('queryengine runtime smoke: controlled failure captured')
}

main().catch(error => {
  console.error(error)
  process.exit(1)
})

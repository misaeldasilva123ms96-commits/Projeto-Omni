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

function classifyImport(specifier) {
  if (specifier.startsWith('bun:')) {
    return {
      specifier,
      status: 'BROKEN',
      kind: 'runtime-only',
      reason: 'Bun runtime dependency is not supported by the default Node ESM loader.',
    }
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
      resolved,
      status: exists ? 'OK' : 'BROKEN',
      kind: 'relative',
      reason: exists ? 'Resolved on disk.' : 'Missing relative module after QueryEngine relocation or incomplete vendoring.',
    }
  }

  if (specifier.startsWith('src/')) {
    return {
      specifier,
      status: 'BROKEN',
      kind: 'alias',
      reason: 'Runtime alias src/* is not configured for this standalone moved file, and the referenced upstream tree is not present.',
    }
  }

  return {
    specifier,
    status: 'EXPECTED_SERVER_DEPENDENCY',
    kind: 'package',
    reason: 'External package or runtime dependency; not validated for installation in this script.',
  }
}

async function main() {
  if (!fs.existsSync(queryEnginePath)) {
    console.log(JSON.stringify({
      ok: false,
      stage: 'file_lookup',
      message: 'runtime/node/QueryEngine.ts not found',
    }, null, 2))
    process.exit(1)
  }

  const source = fs.readFileSync(queryEnginePath, 'utf8')
  const imports = parseImports(source)
  const importGraph = imports.map(classifyImport)

  let importAttempt
  try {
    await import(pathToFileURL(queryEnginePath).href)
    importAttempt = { ok: true, stage: 'import' }
  } catch (error) {
    importAttempt = {
      ok: false,
      stage: 'import',
      name: error?.name || 'Error',
      code: error?.code || 'UNKNOWN',
      message: String(error?.message || error),
    }
  }

  const broken = importGraph.filter(item => item.status === 'BROKEN')
  const summary = {
    ok: importAttempt.ok && broken.length === 0,
    queryengine_path: queryEnginePath,
    import_attempt: importAttempt,
    import_graph: importGraph,
    broken_import_count: broken.length,
    diagnosis:
      broken.length > 0
        ? 'QueryEngine is preserved but not executable as a standalone runtime artifact in this repository state.'
        : 'QueryEngine import graph resolved successfully.',
  }

  console.log(JSON.stringify(summary, null, 2))
  process.exit(summary.ok ? 0 : 1)
}

main()

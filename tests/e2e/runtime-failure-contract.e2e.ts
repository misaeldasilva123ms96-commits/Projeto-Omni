import assert from 'node:assert/strict'


async function main() {
  const baseUrl = process.env.OMNI_E2E_API_URL?.trim()
  assert.ok(baseUrl, 'OMNI_E2E_API_URL is required for the injected-failure contract')

  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: 'analise o arquivo package.json',
      client_session_id: 'e2e-node-failure',
      client_context: { source: 'e2e-runtime-failure-contract' },
    }),
    signal: AbortSignal.timeout(120_000),
  })

  const rawText = await response.text()
  assert.ok(response.ok, `injected failure must remain a controlled HTTP response: ${response.status} ${rawText}`)

  const raw = JSON.parse(rawText) as Record<string, unknown>
  assert.equal(raw.source, 'python-subprocess', 'Rust must preserve the Python boundary evidence')
  assert.equal(raw.stop_reason, 'python_completed', 'the controlled Python fallback must complete')
  assert.ok(
    typeof raw.response === 'string' && raw.response.includes('Modo fallback ativo'),
    'the user-facing response must disclose degraded fallback mode',
  )

  const inspection = raw.cognitive_runtime_inspection
  assert.ok(inspection && typeof inspection === 'object' && !Array.isArray(inspection))
  const runtime = inspection as Record<string, unknown>
  assert.equal(runtime.fallback_triggered, true, 'Node failure must never be reported as healthy success')
  assert.match(String(runtime.runtime_mode), /^NODE_(?:FAILURE|FALLBACK)$/)
  assert.match(String(runtime.runtime_reason), /^NODE_(?:BRIDGE|CIRCUIT)_/)

  console.log('[e2e] injected Node failure is explicit and fail-safe:', {
    stop_reason: raw.stop_reason,
    runtime_mode: runtime.runtime_mode,
    runtime_reason: runtime.runtime_reason,
  })
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})

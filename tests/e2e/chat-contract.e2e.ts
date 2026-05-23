/**
 * E2E + contract validation: Rust → Python → Node stack (HTTP) and wire → UI parity.
 *
 * Fixtures (always run): prove `parseWireChatPayload` + `chatApiResponseToUi` preserve
 * `stop_reason`, `cognitive_runtime_inspection.execution_tier`, and `wireHealth`.
 *
 * Live HTTP (optional): set `OMINI_E2E_API_URL` (e.g. `http://127.0.0.1:3001`) and run the
 * Rust API (`cd backend/rust && PORT=3001 cargo run`). If unset, only fixture checks run.
 */
import assert from 'node:assert/strict'
import { chatApiResponseToUi, parseWireChatPayload } from '../../frontend/src/lib/api/adapters'
import { classifyChatWireHealth } from '../../frontend/src/lib/api/wireChatHealth'

function assertWireUiParity(label: string, raw: Record<string, unknown>) {
  const parsed = parseWireChatPayload(raw)
  const ui = chatApiResponseToUi(parsed)
  const expected = classifyChatWireHealth({
    response: parsed.response,
    stop_reason: parsed.stop_reason,
    cognitive_runtime_inspection: parsed.cognitive_runtime_inspection,
  })
  assert.equal(
    ui.wireHealth,
    expected,
    `${label}: wireHealth must match classifyChatWireHealth`,
  )
}

function runFixtureContracts() {
  assertWireUiParity('degraded-prefix', {
    response: '[degraded:rust_python_boundary] motor indisponivel',
    stop_reason: 'python_empty_stdout',
    cognitive_runtime_inspection: {
      execution_tier: 'technical_fallback',
      rust_boundary: true,
    },
    session_id: 'python-session',
    source: 'python-subprocess',
  })

  assertWireUiParity('degraded-tier-only', {
    response: 'Mensagem util mas boundary degradado',
    stop_reason: 'python_completed',
    cognitive_runtime_inspection: {
      execution_tier: 'technical_fallback',
    },
    session_id: 'python-session',
    source: 'python-subprocess',
  })

  assertWireUiParity('healthy-completed', {
    response: 'Resposta normal do motor.',
    stop_reason: 'python_completed',
    cognitive_runtime_inspection: {
      last_runtime_mode: 'live',
    },
    session_id: 'python-session',
    source: 'python-subprocess',
  })

  const degradedStop = parseWireChatPayload({
    response: 'Fallback texto',
    stop_reason: 'python_subprocess_timeout',
    cognitive_runtime_inspection: { execution_tier: 'technical_fallback' },
    session_id: 'python-session',
    source: 'python-subprocess',
  })
  const uiDegraded = chatApiResponseToUi(degradedStop)
  assert.equal(uiDegraded.wireHealth, 'degraded')
  assert.notEqual(uiDegraded.wireHealth, 'ok', 'timeout stop_reason must not look like clean success')

  const ok = parseWireChatPayload({
    response: 'ok',
    stop_reason: 'python_completed',
    session_id: 'python-session',
    source: 'python-subprocess',
  })
  const uiOk = chatApiResponseToUi(ok)
  assert.equal(uiOk.wireHealth, 'ok')
}

async function tryLiveHttp(baseUrl: string) {
  const url = `${baseUrl.replace(/\/$/, '')}/api/v1/chat`
  const body = {
    message: 'ping e2e contrato',
    client_context: { source: 'e2e-chat-contract' },
  }
  let res: Response
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120_000),
    })
  } catch {
    console.warn('[e2e] live HTTP skipped: server not reachable at', url)
    return
  }

  if (!res.ok) {
    console.warn('[e2e] live HTTP skipped: status', res.status, await res.text())
    return
  }

  const raw = (await res.json()) as Record<string, unknown>
  assert.ok(typeof raw.response === 'string' && raw.response.trim(), 'live: response must be non-empty string')
  assert.ok(typeof raw.stop_reason === 'string' && raw.stop_reason.trim(), 'live: stop_reason must be present')

  const inspection = raw.cognitive_runtime_inspection
  if (inspection && typeof inspection === 'object' && !Array.isArray(inspection)) {
    const tier = (inspection as Record<string, unknown>).execution_tier
    if (typeof tier === 'string') {
      assert.ok(tier.length > 0, 'live: execution_tier string when inspection present')
    }
  }

  assertWireUiParity('live-v1-chat', raw)

  const parsed = parseWireChatPayload(raw)
  const ui = chatApiResponseToUi(parsed)
  if (parsed.stop_reason === 'python_completed' && ui.wireHealth === 'ok') {
    assert.ok(
      !String(parsed.response).startsWith('[degraded:'),
      'live: healthy stop_reason must not pair with degraded body prefix',
    )
  }
  console.log('[e2e] live HTTP ok:', { stop_reason: raw.stop_reason, wireHealth: ui.wireHealth })
}

async function main() {
  runFixtureContracts()
  console.log('[e2e] fixture contracts: ok')

  const base = process.env.OMINI_E2E_API_URL?.trim()
  if (base) {
    await tryLiveHttp(base)
  } else {
    console.warn('[e2e] OMINI_E2E_API_URL unset — skipping live HTTP (fixtures only).')
  }

  console.log('[e2e] chat-contract: done')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})

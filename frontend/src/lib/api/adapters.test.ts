import { describe, expect, it } from 'vitest'
import { chatApiResponseToUi, parseWireChatPayload } from './adapters'

const snapshot = {
  providers: [
    { id: 'groq', registered: true, configured: true, adapter_implemented: true, executable: true, execution_status: 'active' },
    { id: 'openrouter', registered: true, configured: false, adapter_implemented: true, executable: false, execution_status: 'credential_gated' },
    { id: 'openai', registered: true, configured: false, adapter_implemented: true, executable: false, execution_status: 'credential_gated' },
    { id: 'anthropic', registered: true, configured: false, adapter_implemented: true, executable: false, execution_status: 'credential_gated' },
    { id: 'gemini', registered: true, configured: false, adapter_implemented: true, executable: false, execution_status: 'credential_gated' },
    { id: 'ollama', registered: true, configured: false, adapter_implemented: true, executable: false, execution_status: 'local_config_gated' },
    { id: 'lmstudio', registered: true, configured: false, adapter_implemented: true, executable: false, execution_status: 'local_config_gated' },
    { id: 'deepseek', registered: true, configured: false, adapter_implemented: false, executable: false, execution_status: 'unsupported' },
  ],
  fallback_chain: ['groq', 'openrouter', 'openai', 'anthropic', 'gemini', 'ollama', 'lmstudio', 'local-heuristic'],
  active_provider: 'groq',
  fallback_triggered: false,
  fallback_reason: null,
}

describe('chat API provider diagnostics compatibility', () => {
  it('preserves the client-owned session for UI continuity while backend exposes runtime session', () => {
    const ui = chatApiResponseToUi({
      response: 'ok',
      session_id: 'runtime-session-1',
      client_session_id: 'client-session-1',
    })
    expect(ui.sessionId).toBe('client-session-1')

    const runtimeOnly = chatApiResponseToUi({
      response: 'ok',
      session_id: 'runtime-session-2',
    })
    expect(runtimeOnly.sessionId).toBe('runtime-session-2')
  })

  it('keeps legacy provider_diagnostics as an array when snapshot is present', () => {
    const wire = parseWireChatPayload({
      response: 'ok',
      provider_diagnostics: [
        {
          provider: 'groq',
          configured: true,
          available: true,
          selected: true,
          attempted: true,
          succeeded: true,
          failed: false,
          latency_ms: 42,
        },
      ],
      provider_diagnostics_snapshot: snapshot,
    })

    expect(Array.isArray(wire.provider_diagnostics)).toBe(true)
    expect(wire.provider_diagnostics).toHaveLength(1)
    expect(wire.provider_diagnostics?.find((row) => row.provider === 'groq')?.selected).toBe(true)
    expect(JSON.stringify(wire)).not.toContain('provider_diagnostics_snapshot')

    const ui = chatApiResponseToUi(wire)
    expect(Array.isArray(ui.providerDiagnostics)).toBe(true)
    expect(ui.providerDiagnostics).toHaveLength(1)
    expect(ui.providerDiagnostics?.map((row) => row.provider)).toEqual(['groq'])
  })

  it('ignores snapshot-shaped provider_diagnostics so legacy consumers keep array semantics', () => {
    const wire = parseWireChatPayload({
      response: 'ok',
      provider_diagnostics: snapshot,
      signals: {
        provider_diagnostics: [
          {
            provider: 'openai',
            configured: true,
            available: true,
            selected: true,
            attempted: true,
            succeeded: false,
            failed: true,
            failure_class: 'provider_failure',
          },
        ],
      },
      provider_diagnostics_snapshot: snapshot,
    })

    expect(Array.isArray(wire.provider_diagnostics)).toBe(true)
    expect(wire.provider_diagnostics).toHaveLength(1)
    expect(wire.provider_diagnostics?.[0].provider).toBe('openai')

    const ui = chatApiResponseToUi(wire)
    expect(ui.providerDiagnostics?.length).toBe(1)
    expect(ui.providerDiagnostics?.find((row) => row.provider === 'openai')?.failed).toBe(true)
  })

  it('preserves optional provider model and token telemetry when present', () => {
    const wire = parseWireChatPayload({
      response: 'ok',
      provider_diagnostics: [{
        provider: 'openai',
        model: 'gpt-runtime',
        attempted: true,
        succeeded: true,
        latency_ms: 55,
        tokens_in: 18,
        tokens_out: 7,
      }],
    })

    expect(wire.provider_diagnostics?.[0]).toMatchObject({
      provider: 'openai',
      model: 'gpt-runtime',
      tokens_in: 18,
      tokens_out: 7,
    })
  })
})

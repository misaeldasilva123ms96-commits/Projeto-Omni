import { describe, expect, it } from 'vitest'
import type { UiChatResponse } from '../types/ui/chat'
import {
  normalizeStoredRuntimeMetadata,
  normalizeUiChatRuntime,
} from './runtimeNormalizer'

describe('normalizeUiChatRuntime', () => {
  it('maps a full live chat response into metadata and inspector contracts', () => {
    const ui: UiChatResponse = {
      text: 'ok',
      sessionId: 'server-session',
      commands: [],
      tools: ['read_file'],
      usage: { inputTokens: 44, outputTokens: 12 },
      cognitiveRuntimeInspection: {
        runtime_mode: 'FULL_COGNITIVE_RUNTIME',
        runtime_reason: 'node_execution',
        llm_provider_attempted: true,
        llm_provider_succeeded: true,
        tool_invoked: true,
        fallback_triggered: false,
        provider_actual: 'openai',
        latency_ms: 91,
        request_id: 'req-normalizer-1',
        governance: {
          decision: 'allowed',
          risk_level: 'low',
          blocked: false,
          reason: 'policy passed',
          policy: 'default',
          tool_category: 'read',
          requires_approval: false,
        },
        oil: {
          input: { prompt: 'safe' },
          decision: 'execute',
          execution: { status: 'completed' },
          observation: { result: 'ok' },
          evaluation: { accepted: true },
        },
      },
      providerDiagnostics: [{
        provider: 'openai',
        selected: true,
        attempted: true,
        succeeded: true,
        latency_ms: 91,
      }],
      toolExecution: {
        tool_selected: 'read_file',
        tool_attempted: true,
        tool_succeeded: true,
      },
      wireHealth: 'ok',
    }

    const snapshot = normalizeUiChatRuntime(ui, 'client-session')

    expect(snapshot.metadata.sessionId).toBe('server-session')
    expect(snapshot.inspectorData?.summary).toMatchObject({
      runtime_mode: 'FULL_COGNITIVE_RUNTIME',
      provider_attempted: true,
      provider_succeeded: true,
      tool_invoked: true,
      tokens_in: 44,
      tokens_out: 12,
      request_id: 'req-normalizer-1',
    })
    expect(snapshot.inspectorData?.governance?.decision).toBe('allowed')
    expect(snapshot.inspectorData?.provider?.provider_name).toBe('openai')
    expect(snapshot.inspectorData?.oil?.decision).toBe('execute')
  })

  it('returns a safe empty inspector snapshot when chat metadata is absent', () => {
    const snapshot = normalizeUiChatRuntime({
      text: 'chat still succeeds',
      commands: [],
      tools: [],
      wireHealth: 'ok',
    }, 'client-session')

    expect(snapshot.metadata.sessionId).toBe('client-session')
    expect(snapshot.inspectorData).toBeNull()
  })

  it('redacts sensitive live fields before they reach inspector data', () => {
    const snapshot = normalizeUiChatRuntime({
      text: 'ok',
      commands: [],
      tools: [],
      cognitiveRuntimeInspection: {
        runtime_mode: 'SAFE_FALLBACK',
        runtime_reason: 'Bearer should-not-render',
        request_id: 'req-safe',
        oil: {
          input: { authorization: 'Bearer should-not-render' },
        },
      },
      wireHealth: 'degraded',
    }, 'client-session')

    const serialized = JSON.stringify(snapshot.inspectorData)
    expect(serialized).not.toContain('should-not-render')
    expect(serialized).not.toContain('authorization')
    expect(serialized).toContain('[REDACTED]')
  })

  it('falls back safely for malformed persisted runtime metadata', () => {
    expect(() => normalizeStoredRuntimeMetadata({} as never)).not.toThrow()
    expect(normalizeStoredRuntimeMetadata({} as never)).toBeNull()
  })
})

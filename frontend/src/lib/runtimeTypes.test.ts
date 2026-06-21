import { describe, expect, it } from 'vitest'
import type { RuntimeMetadata } from '../types'
import {
  normalizeRuntimeInspectorData,
  normalizeRuntimeMode,
} from './runtimeTypes'

describe('runtime inspector contracts', () => {
  it('normalizes runtime modes to the allowed contract', () => {
    expect(normalizeRuntimeMode('FULL_COGNITIVE_RUNTIME')).toBe('FULL_COGNITIVE_RUNTIME')
    expect(normalizeRuntimeMode('unexpected-mode')).toBe('UNKNOWN')
    expect(normalizeRuntimeMode(null)).toBe('UNKNOWN')
  })

  it('projects available runtime truth without inventing missing values', () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: ['read_file'],
      runtimeMode: 'PARTIAL_COGNITIVE',
      runtimeReason: 'provider_degraded',
      fallbackTriggered: true,
      usage: { input_tokens: 12, output_tokens: 7 },
      cognitiveRuntimeInspection: {
        provider_attempted: true,
        provider_succeeded: false,
        tool_invoked: true,
        governance_decision: 'requires_approval',
        request_id: 'req-1',
        trace_id: 'trace-1',
        created_at: '2026-06-17T12:00:00Z',
        governance: {
          decision: 'requires_approval',
          risk_level: 'high',
          blocked: false,
          reason: 'human review',
          policy: 'tool-policy',
          tool_category: 'filesystem',
          requires_approval: true,
        },
        provider: {
          provider_name: 'openai',
          model: 'gpt-test',
          attempted: true,
          succeeded: false,
          failure_reason: 'unavailable',
          latency_ms: 42,
          tokens_in: 12,
          tokens_out: 7,
        },
        oil: {
          input: { prompt: 'safe' },
          decision: 'review',
          execution: null,
          observation: null,
          evaluation: null,
        },
      },
    }

    const normalized = normalizeRuntimeInspectorData(metadata)

    expect(normalized.summary).toMatchObject({
      runtime_mode: 'PARTIAL_COGNITIVE',
      runtime_reason: 'provider_degraded',
      provider_attempted: true,
      provider_succeeded: false,
      fallback_triggered: true,
      tool_invoked: true,
      governance_decision: 'requires_approval',
      tokens_in: 12,
      tokens_out: 7,
      request_id: 'req-1',
      trace_id: 'trace-1',
      created_at: '2026-06-17T12:00:00Z',
    })
    expect(normalized.governance).toMatchObject({
      decision: 'requires_approval',
      risk_level: 'high',
      requires_approval: true,
    })
    expect(normalized.provider).toMatchObject({
      provider_name: 'openai',
      model: 'gpt-test',
      attempted: true,
      succeeded: false,
    })
    expect(normalized.oil?.input).toEqual({ prompt: 'safe' })
  })

  it('returns safe empty contracts when metadata is unavailable', () => {
    const normalized = normalizeRuntimeInspectorData(null)

    expect(normalized.summary.runtime_mode).toBe('UNKNOWN')
    expect(normalized.summary.runtime_reason).toBeNull()
    expect(normalized.governance).toBeNull()
    expect(normalized.provider).toBeNull()
    expect(normalized.tools).toEqual([])
    expect(normalized.memory).toBeNull()
    expect(normalized.oil).toBeNull()
    expect(normalized.logs).toBeNull()
  })

  it('preserves the existing provider label when diagnostics are unavailable', () => {
    const normalized = normalizeRuntimeInspectorData({
      matchedCommands: [],
      matchedTools: [],
      providerActual: 'openai',
    })

    expect(normalized.provider?.provider_name).toBe('openai')
    expect(normalized.providers).toHaveLength(1)
  })

  it('maps public live runtime truth aliases from cognitive runtime inspection', () => {
    const normalized = normalizeRuntimeInspectorData({
      matchedCommands: [],
      matchedTools: [],
      usage: { input_tokens: 31, output_tokens: 17 },
      cognitiveRuntimeInspection: {
        runtime_mode: 'FULL_COGNITIVE_RUNTIME',
        runtime_reason: 'node_execution',
        llm_provider_attempted: true,
        llm_provider_succeeded: true,
        tool_invoked: true,
        fallback_triggered: false,
        provider_actual: 'openai',
        latency_ms: 84,
        request_id: 'req-live-1',
      },
    })

    expect(normalized.summary).toMatchObject({
      runtime_mode: 'FULL_COGNITIVE_RUNTIME',
      runtime_reason: 'node_execution',
      provider_attempted: true,
      provider_succeeded: true,
      tool_invoked: true,
      fallback_triggered: false,
      tokens_in: 31,
      tokens_out: 17,
      latency_ms: 84,
      request_id: 'req-live-1',
    })
    expect(normalized.provider?.provider_name).toBe('openai')
  })

  it('prefers valid inspection token values and preserves an explicit total', () => {
    const normalized = normalizeRuntimeInspectorData({
      matchedCommands: [],
      matchedTools: [],
      usage: { input_tokens: 90, output_tokens: 40, total_tokens: 130 },
      cognitiveRuntimeInspection: {
        tokens_in: 12,
        tokens_out: 8,
        total_tokens: 25,
      },
    })

    expect(normalized.summary).toMatchObject({
      tokens_in: 12,
      tokens_out: 8,
      total_tokens: 25,
    })
  })

  it('ignores invalid higher-priority token values and falls back to valid usage', () => {
    const normalized = normalizeRuntimeInspectorData({
      matchedCommands: [],
      matchedTools: [],
      usage: { input_tokens: 9, output_tokens: 4 },
      cognitiveRuntimeInspection: {
        tokens_in: -1,
        tokens_out: 2.5,
        total_tokens: Number.POSITIVE_INFINITY,
      },
    })

    expect(normalized.summary).toMatchObject({
      tokens_in: 9,
      tokens_out: 4,
      total_tokens: 13,
    })
  })

  it('maps governance scalar fields when a nested governance object is unavailable', () => {
    const normalized = normalizeRuntimeInspectorData({
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        runtime_mode: 'PARTIAL_COGNITIVE',
        governance_decision: 'requires_approval',
        risk_level: 'high',
        blocked: false,
        reason: 'review required',
        policy: 'tool-policy',
        tool_category: 'filesystem',
        requires_approval: true,
      },
    })

    expect(normalized.governance).toMatchObject({
      decision: 'requires_approval',
      risk_level: 'high',
      blocked: false,
      reason: 'review required',
      policy: 'tool-policy',
      tool_category: 'filesystem',
      requires_approval: true,
    })
  })
})

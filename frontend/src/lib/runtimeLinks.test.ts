import { describe, expect, it } from 'vitest'
import type { RuntimeInspectorData } from './runtimeTypes'
import {
  buildRuntimeInspectorLinks,
  buildSafeRuntimeHref,
} from './runtimeLinks'

function inspectorData(): RuntimeInspectorData {
  return {
    summary: {
      runtime_mode: 'FULL_COGNITIVE_RUNTIME',
      runtime_reason: 'node_execution',
      provider_attempted: true,
      provider_succeeded: true,
      fallback_triggered: false,
      tool_invoked: true,
      governance_decision: 'allowed',
      tokens_in: 20,
      tokens_out: 8,
      total_tokens: 28,
      latency_ms: 40,
      request_id: 'req-safe-1',
      trace_id: 'trace-safe-1',
      created_at: null,
    },
    governance: {
      decision: 'allowed',
      risk_level: 'low',
      blocked: false,
      reason: 'policy passed',
      policy: 'default',
      tool_category: 'read',
      requires_approval: false,
    },
    tools: [{
      tool_selected: 'read_file',
      tool_attempted: true,
      tool_succeeded: true,
    }],
    provider: {
      provider_name: 'openai',
      model: null,
      attempted: true,
      succeeded: true,
      failure_reason: null,
      latency_ms: 40,
      tokens_in: 20,
      tokens_out: 8,
      total_tokens: 28,
    },
    providers: [],
    memory: null,
    oil: null,
    autonomy: null,
    logs: { runtime_mode: 'FULL_COGNITIVE_RUNTIME' },
  }
}

describe('runtime inspector links', () => {
  it('generates links only with allowed safe query parameters', () => {
    const links = buildRuntimeInspectorLinks(inspectorData())

    expect(links.observability).toBe(
      '/observability?request_id=req-safe-1&trace_id=trace-safe-1&runtime_mode=FULL_COGNITIVE_RUNTIME',
    )
    expect(links.provider).toBe('/provider-center?provider=openai')
    expect(links.tool).toBe(
      '/observability?request_id=req-safe-1&trace_id=trace-safe-1&runtime_mode=FULL_COGNITIVE_RUNTIME&tool=read_file',
    )
    expect(links.governance).toBe('/governance?decision=allowed')
    expect(links.logs).toBe(links.observability)

    for (const href of Object.values(links)) {
      if (!href) continue
      const url = new URL(href, 'https://omni.local')
      for (const key of url.searchParams.keys()) {
        expect([
          'request_id',
          'trace_id',
          'runtime_mode',
          'provider',
          'tool',
          'decision',
        ]).toContain(key)
      }
    }
  })

  it('rejects secret-like values and ignores forbidden parameter names', () => {
    const href = buildSafeRuntimeHref('observability', {
      request_id: 'Bearer should-not-render',
      trace_id: 'trace-safe',
      token: 'sk-proj-should-not-render',
      payload: '{"secret":"hidden"}',
      prompt: 'private prompt',
    } as Record<string, unknown>)

    expect(href).toBe('/observability?trace_id=trace-safe')
    expect(href).not.toContain('Bearer')
    expect(href).not.toContain('token')
    expect(href).not.toContain('payload')
    expect(href).not.toContain('prompt')
    expect(href).not.toContain('should-not-render')
  })

  it('returns null links when safe references or destinations are unavailable', () => {
    const data = inspectorData()
    data.summary.request_id = null
    data.summary.trace_id = null
    data.summary.runtime_mode = 'UNKNOWN'
    data.summary.governance_decision = null
    data.provider = null
    data.tools = []
    data.governance = null
    data.logs = null

    expect(buildRuntimeInspectorLinks(data)).toEqual({
      observability: null,
      provider: null,
      tool: null,
      governance: null,
      logs: null,
    })
  })

  it('does not create a tool execution link without an invoked tool', () => {
    const data = inspectorData()
    data.tools = []

    const links = buildRuntimeInspectorLinks(data)

    expect(links.observability).not.toBeNull()
    expect(links.tool).toBeNull()
  })
})

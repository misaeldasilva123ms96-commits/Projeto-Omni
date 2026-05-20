/**
 * Tests for Phase 1D — Frontend debug sanitization.
 * Run: pnpm test (or vitest run)
 */

import { describe, it, expect } from 'vitest'
import {
  sanitizeRuntimeDebugPayload,
  sanitizeRuntimeDebugPayloadStrict,
} from '../lib/runtimeDebugSanitizer'

describe('sanitizeRuntimeDebugPayload', () => {
  it('removes stack field', () => {
    const result = sanitizeRuntimeDebugPayload({ runtime_mode: 'FULL', stack: 'Error at line 1' })
    expect(result).not.toHaveProperty('stack')
  })

  it('removes command field', () => {
    const result = sanitizeRuntimeDebugPayload({ runtime_mode: 'FULL', command: 'rm -rf /' })
    expect(result).not.toHaveProperty('command')
  })

  it('removes env field', () => {
    const result = sanitizeRuntimeDebugPayload({ runtime_mode: 'FULL', env: { SECRET: 'abc' } })
    expect(result).not.toHaveProperty('env')
  })

  it('removes token field', () => {
    const result = sanitizeRuntimeDebugPayload({ runtime_mode: 'FULL', token: 'secret123' })
    expect(result).not.toHaveProperty('token')
  })

  it('removes stdout field', () => {
    const result = sanitizeRuntimeDebugPayload({ runtime_mode: 'FULL', stdout: 'output data' })
    expect(result).not.toHaveProperty('stdout')
  })

  it('removes stderr field', () => {
    const result = sanitizeRuntimeDebugPayload({ runtime_mode: 'FULL', stderr: 'error output' })
    expect(result).not.toHaveProperty('stderr')
  })

  it('removes field containing "raw" fragment', () => {
    const result = sanitizeRuntimeDebugPayload({ tool_raw_result: 'sensitive' })
    expect(result).not.toHaveProperty('tool_raw_result')
  })

  it('preserves runtime_mode', () => {
    const result = sanitizeRuntimeDebugPayload({ runtime_mode: 'MATCHER_SHORTCUT' })
    expect(result.runtime_mode).toBe('MATCHER_SHORTCUT')
  })

  it('preserves fallback_triggered', () => {
    const result = sanitizeRuntimeDebugPayload({ fallback_triggered: true })
    expect(result.fallback_triggered).toBe(true)
  })

  it('removes nested stack trace', () => {
    const result = sanitizeRuntimeDebugPayload({
      runtime: { runtime_mode: 'FULL', stack: 'err...' },
    })
    expect((result.runtime as Record<string, unknown>)).not.toHaveProperty('stack')
    expect((result.runtime as Record<string, unknown>).runtime_mode).toBe('FULL')
  })

  it('handles null input gracefully', () => {
    const result = sanitizeRuntimeDebugPayload(null)
    expect(result).toEqual({})
  })

  it('handles non-object input gracefully', () => {
    const result = sanitizeRuntimeDebugPayload('string input')
    expect(result).toEqual({})
  })
})

describe('sanitizeRuntimeDebugPayloadStrict', () => {
  it('only allows whitelisted keys', () => {
    const result = sanitizeRuntimeDebugPayloadStrict({
      runtime_mode: 'FULL',
      some_internal_field: 'should be removed',
    })
    expect(result).toHaveProperty('runtime_mode')
    expect(result).not.toHaveProperty('some_internal_field')
  })
})

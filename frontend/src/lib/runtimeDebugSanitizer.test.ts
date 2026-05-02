import { describe, expect, it } from 'vitest'
import { sanitizeRuntimeDebugPayload } from './runtimeDebugSanitizer'

function text(value: unknown) {
  return JSON.stringify(value)
}

describe('sanitizeRuntimeDebugPayload', () => {
  it('removes dangerous debug keys recursively', () => {
    const sanitized = sanitizeRuntimeDebugPayload({
      runtime_mode: 'SAFE_FALLBACK',
      stack: 'stack',
      trace: 'trace',
      traceback: 'traceback',
      command: 'node runner',
      args: ['--secret'],
      stdout: 'raw stdout',
      stderr: 'raw stderr',
      env: { OPENAI_API_KEY: 'sk-proj-abcdefghijklmnop' },
      token: 'secret-token',
      secret: 'hidden',
      password: 'hidden',
      api_key: 'sk-proj-abcdefghijklmnop',
      jwt: 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature',
      raw_payload: { value: 'hidden' },
      raw_key: 'hidden',
      raw_url: 'https://example.supabase.co',
      execution_request: { actions: [] },
      nested: {
        provider_raw: { body: 'raw' },
        raw_response: 'raw',
        tool_raw_result: 'raw tool',
        memory_content: 'private',
        safe: 'kept',
      },
    })

    const payload = text(sanitized)
    for (const fragment of [
      'stack',
      'trace',
      'traceback',
      'command',
      'args',
      'stdout',
      'stderr',
      'env',
      'OPENAI_API_KEY',
      'token',
      'secret-token',
      'hidden',
      'password',
      'api_key',
      'jwt',
      'raw_payload',
      'raw_key',
      'raw_url',
      'execution_request',
      'provider_raw',
      'raw_response',
      'tool_raw_result',
      'memory_content',
    ]) {
      expect(payload).not.toContain(fragment)
    }
    expect(sanitized.runtime_mode).toBe('SAFE_FALLBACK')
    expect((sanitized.nested as Record<string, unknown>).safe).toBe('kept')
  })

  it('redacts sensitive debug string values', () => {
    const sanitized = sanitizeRuntimeDebugPayload({
      public_summary:
        'Paths /home/render/project/.env /root/secret /tmp/x /var/log/app /usr/bin/node /etc/passwd ' +
        'C:\\Users\\Misael\\secret.txt C:\\Windows\\System32\\config C:\\Program Files\\Omni\\secret.txt ' +
        'sk-proj-abcdefghijklmnop Bearer abcdefghijklmnopqrstuvwxyz ' +
        'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature https://project.supabase.co user@example.com +55 11 99999-9999',
    })
    const payload = text(sanitized)

    expect(payload).not.toContain('/home/render')
    expect(payload).not.toContain('/root/secret')
    expect(payload).not.toContain('/tmp/x')
    expect(payload).not.toContain('/var/log')
    expect(payload).not.toContain('/usr/bin')
    expect(payload).not.toContain('/etc/passwd')
    expect(payload).not.toContain('C:\\Users\\Misael')
    expect(payload).not.toContain('C:\\Windows')
    expect(payload).not.toContain('C:\\Program Files')
    expect(payload).not.toContain('sk-proj-')
    expect(payload).not.toContain('Bearer abcdefghijklmnopqrstuvwxyz')
    expect(payload).not.toContain('eyJhbGci')
    expect(payload).not.toContain('project.supabase.co')
    expect(payload).not.toContain('user@example.com')
    expect(payload).not.toContain('+55 11 99999-9999')
    expect(payload).toContain('[redacted_location]')
    expect(payload).toContain('[redacted_secret]')
    expect(payload).toContain('[redacted_email]')
    expect(payload).toContain('[redacted_phone]')
  })

  it('preserves public runtime, provider, and tool fields', () => {
    const sanitized = sanitizeRuntimeDebugPayload({
      runtime_mode: 'FULL_COGNITIVE_RUNTIME',
      runtime_lane: 'true_action_execution',
      degraded: false,
      fallback_triggered: false,
      provider_public_name: 'openai',
      provider_actual: 'openai',
      provider_attempted: 'openai',
      provider_succeeded: true,
      provider_failed: false,
      tool_invoked: true,
      tool_status: 'succeeded',
      tool_public_name: 'read_file',
      latency_ms: 42,
      request_id: 'req-1',
      warnings_public: ['none'],
      error_public_code: 'NONE',
      error_public_message: '',
      internal_error_redacted: true,
      public_summary: 'Full cognitive execution with provider and tool verification.',
      final_verdict: 'TRUE_COGNITIVE_RUNTIME',
      source_of_truth: 'Node',
    })

    expect(sanitized.runtime_mode).toBe('FULL_COGNITIVE_RUNTIME')
    expect(sanitized.runtime_lane).toBe('true_action_execution')
    expect(sanitized.fallback_triggered).toBe(false)
    expect(sanitized.provider_public_name).toBe('openai')
    expect(sanitized.provider_actual).toBe('openai')
    expect(sanitized.tool_status).toBe('succeeded')
    expect(sanitized.tool_public_name).toBe('read_file')
    expect(sanitized.public_summary).toBe('Full cognitive execution with provider and tool verification.')
    expect(sanitized.final_verdict).toBe('TRUE_COGNITIVE_RUNTIME')
  })

  it('does not mutate the original object and tolerates non-object input', () => {
    const original = {
      runtime_mode: 'SAFE_FALLBACK',
      nested: { stderr: 'raw', public_summary: 'safe' },
    }
    const before = structuredClone(original)

    const sanitized = sanitizeRuntimeDebugPayload(original)

    expect(original).toEqual(before)
    expect(text(sanitized)).not.toContain('stderr')
    expect(sanitizeRuntimeDebugPayload(null)).toEqual({})
    expect(sanitizeRuntimeDebugPayload('debug')).toEqual({})
  })
})

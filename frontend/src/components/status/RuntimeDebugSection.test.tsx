import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { RuntimeMetadata } from '../../types'
import { RuntimeDebugSection } from './RuntimeDebugSection'

describe('RuntimeDebugSection', () => {
  it('renders public runtime diagnostics without raw debug payloads', () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      runtimeMode: 'SAFE_FALLBACK',
      runtimeReason: '/home/render/project/.env sk-proj-abcdefghijklmnop',
      executionPathUsed: 'node_execution',
      fallbackTriggered: true,
      providerActual: 'openai',
      providerFailed: true,
      failureClass: 'provider_failure',
      failureReason: 'Bearer abcdefghijklmnopqrstuvwxyz',
      cognitiveRuntimeInspection: {
        runtime_mode: 'SAFE_FALLBACK',
        public_summary: 'System operated in safe fallback mode due to runtime constraints.',
        stack: 'raw stack',
        traceback: 'traceback',
      },
      signals: {
        runtime_reason: 'node_failure',
        execution_provenance: {
          command: 'node js-runner/queryEngineRunner.js',
          raw_response: 'provider raw',
          provider_actual: 'openai',
        },
        provider_diagnostics: [
          {
            provider: 'openai',
            failed: true,
            failure_reason: 'C:\\Users\\Misael\\secret.txt',
          },
        ],
        tool_execution: {
          tool_selected: 'read_file',
          tool_succeeded: false,
          tool_failure_reason: 'user@example.com +55 11 99999-9999',
        },
        tool_diagnostics: [{ tool_selected: 'read_file', tool_raw_result: 'raw tool' }],
      } as unknown as RuntimeMetadata['signals'],
      error: {
        error_public_code: 'SPECIALIST_FAILED',
        error_public_message: 'Specialist execution failed. Using fallback.',
        severity: 'degraded',
        retryable: true,
        internal_error_redacted: true,
        details: { env: { SECRET: 'hidden' } },
      },
    }

    render(<RuntimeDebugSection metadata={metadata} />)

    expect(screen.getByText('Runtime debug (last turn)')).toBeInTheDocument()
    expect(screen.getAllByText('SAFE_FALLBACK').length).toBeGreaterThan(0)
    expect(screen.getAllByText('openai').length).toBeGreaterThan(0)
    expect(screen.getByText('SPECIALIST_FAILED')).toBeInTheDocument()
    expect(screen.getByText('degraded')).toBeInTheDocument()

    const html = document.body.textContent ?? ''
    expect(html).not.toContain('/home/render')
    expect(html).not.toContain('sk-proj-')
    expect(html).not.toContain('Bearer abcdefghijklmnopqrstuvwxyz')
    expect(html).not.toContain('raw stack')
    expect(html).not.toContain('traceback')
    expect(html).not.toContain('command')
    expect(html).not.toContain('raw_response')
    expect(html).not.toContain('provider raw')
    expect(html).not.toContain('C:\\Users\\Misael')
    expect(html).not.toContain('tool_raw_result')
    expect(html).not.toContain('raw tool')
    expect(html).not.toContain('user@example.com')
    expect(html).not.toContain('+55 11 99999-9999')
    expect(html).not.toContain('C:\\Windows')
    expect(html).not.toContain('SECRET')
  })
})

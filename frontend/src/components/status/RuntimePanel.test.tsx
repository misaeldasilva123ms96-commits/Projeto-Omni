import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { RuntimeMetadata } from '../../types'
import { RuntimePanel } from './RuntimePanel'

describe('RuntimePanel', () => {
  it('renders with no metadata', () => {
    render(
      <RuntimePanel
        health={null}
        lastMetadata={null}
        modeLabel="Chat"
        requestState="idle"
        sessionId="session-test"
      />,
    )

    expect(screen.getByText('Runtime Status')).toBeInTheDocument()
    expect(screen.getByText('Chat')).toBeInTheDocument()
  })

  it('renders with metadata and debug payload', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: ['Criar plano'],
      matchedTools: [],
      runtimeMode: 'FULL_COGNITIVE_RUNTIME',
      runtimeReason: 'node_execution',
      executionPathUsed: 'node_execution',
      providerActual: 'openai',
      providerDiagnostics: [{ provider: 'openai', selected: true, latency_ms: 123 }],
    }

    render(
      <RuntimePanel
        health={null}
        lastMetadata={metadata}
        modeLabel="Chat"
        requestState="idle"
        sessionId="session-test"
      />,
    )

    expect(screen.getByText('FULL_COGNITIVE_RUNTIME')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Debug/i }))
    expect(screen.getByText('Debug Mode')).toBeInTheDocument()
    expect(screen.getByText('openai')).toBeInTheDocument()
  })
})

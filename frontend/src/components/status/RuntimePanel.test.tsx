import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { RuntimeMetadata } from '../../types'
import { normalizeStoredRuntimeMetadata } from '../../lib/runtimeNormalizer'
import { RuntimePanel } from './RuntimePanel'

describe('RuntimePanel', () => {
  it('renders with no metadata', () => {
    render(
      <RuntimePanel
        health={null}
        inspectorData={null}
        lastMetadata={null}
        modeLabel="Chat"
        requestState="idle"
        sessionId="session-test"
      />,
    )

    expect(screen.getByRole('tab', { name: 'Summary' })).toBeInTheDocument()
    expect(screen.getByText('não disponível')).toBeInTheDocument()
  })

  it('renders with metadata and shows summary + safe logs', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: ['Criar plano'],
      matchedTools: [],
      runtimeMode: 'FULL_COGNITIVE_RUNTIME',
      runtimeReason: 'node_execution',
      executionPathUsed: 'node_execution',
      providerActual: 'openai',
      providerDiagnostics: [{ provider: 'openai', selected: true, latency_ms: 123 }],
      cognitiveRuntimeInspection: {
        public_summary: 'Full cognitive execution with provider and tool verification.',
        stack: 'raw-stack',
        execution_request: { actions: [{ name: 'danger' }] },
      },
      signals: {
        stderr: 'raw stderr',
        token: 'sk-proj-abcdefghijklmnop',
      } as unknown as RuntimeMetadata['signals'],
    }

    render(
      <RuntimePanel
        health={null}
        inspectorData={normalizeStoredRuntimeMetadata(metadata)}
        lastMetadata={metadata}
        modeLabel="Chat"
        requestState="idle"
        sessionId="session-test"
      />,
    )

    expect(screen.getByText('FULL_COGNITIVE_RUNTIME')).toBeInTheDocument()
    expect(screen.getByText('BYOK')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'Logs' }))
    expect(screen.getByText('Safe Debug Log')).toBeInTheDocument()
    expect(screen.queryByText(/raw-stack/)).not.toBeInTheDocument()
    expect(screen.queryByText(/execution_request/)).not.toBeInTheDocument()
    expect(screen.queryByText(/raw stderr/)).not.toBeInTheDocument()
    expect(screen.queryByText(/sk-proj-/)).not.toBeInTheDocument()
  })
})

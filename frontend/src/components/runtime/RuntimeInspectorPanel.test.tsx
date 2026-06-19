import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { RuntimeMetadata } from '../../types'
import { normalizeStoredRuntimeMetadata } from '../../lib/runtimeNormalizer'
import { RuntimeInspectorPanel } from './RuntimeInspectorPanel'

describe('RuntimeInspectorPanel', () => {
  it('renders a safe empty state for every tab when runtime data is missing', async () => {
    render(
      <RuntimeInspectorPanel
        data={null}
        requestState="idle"
      />,
    )

    for (const tab of ['Summary', 'Governance', 'Tools', 'Provider', 'Memory', 'OIL', 'Logs']) {
      await userEvent.click(screen.getByRole('tab', { name: tab }))
      expect(screen.getByText('não disponível')).toBeInTheDocument()
    }
  })

  it('redacts OIL payloads before rendering them', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        oil: {
          input: { authorization: 'Bearer should-not-render' },
          decision: { api_key: 'sk-proj-should-not-render' },
          execution: null,
          observation: null,
          evaluation: null,
        },
      },
    }

    render(
      <RuntimeInspectorPanel
        data={normalizeStoredRuntimeMetadata(metadata)}
        requestState="idle"
      />,
    )

    await userEvent.click(screen.getByRole('tab', { name: 'OIL' }))

    expect(screen.getAllByText('"[REDACTED]"').length).toBeGreaterThan(0)
    expect(document.body.textContent).not.toContain('should-not-render')
    expect(document.body.textContent).not.toContain('authorization')
    expect(document.body.textContent).not.toContain('api_key')
  })

  it('redacts sensitive scalar contract values before rendering them', () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      runtimeMode: 'SAFE_FALLBACK',
      runtimeReason: 'Bearer should-not-render',
      cognitiveRuntimeInspection: {
        governance: {
          decision: 'blocked',
          reason: 'sk-proj-should-not-render',
        },
      },
    }

    render(
      <RuntimeInspectorPanel
        data={normalizeStoredRuntimeMetadata(metadata)}
        requestState="idle"
      />,
    )

    expect(screen.getByText('[REDACTED]')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('should-not-render')
  })

  it('renders safe navigation links for available runtime references', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: ['read_file'],
      runtimeMode: 'FULL_COGNITIVE_RUNTIME',
      providerActual: 'openai',
      cognitiveRuntimeInspection: {
        request_id: 'req-link-1',
        trace_id: 'trace-link-1',
        governance: { decision: 'allowed' },
      },
      toolExecution: {
        tool_selected: 'read_file',
        tool_attempted: true,
        tool_succeeded: true,
      },
    }

    render(
      <RuntimeInspectorPanel
        data={normalizeStoredRuntimeMetadata(metadata)}
        requestState="idle"
      />,
    )

    expect(screen.getByRole('link', { name: 'Abrir em Observabilidade' })).toHaveAttribute(
      'href',
      '/observability?request_id=req-link-1&trace_id=trace-link-1&runtime_mode=FULL_COGNITIVE_RUNTIME',
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Tools' }))
    expect(screen.getByRole('link', { name: 'Ver execução' })).toHaveAttribute(
      'href',
      expect.stringContaining('tool=read_file'),
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Provider' }))
    expect(screen.getByRole('link', { name: 'Ver provider' })).toHaveAttribute(
      'href',
      '/provider-center?provider=openai',
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Governance' }))
    expect(screen.getByRole('link', { name: 'Ver decisão' })).toHaveAttribute(
      'href',
      '/governance?decision=allowed',
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Logs' }))
    expect(screen.getByRole('link', { name: 'Ver logs seguros' })).toHaveAttribute(
      'href',
      expect.stringContaining('request_id=req-link-1'),
    )
  })

  it('renders disabled navigation states when references are unavailable', async () => {
    render(
      <RuntimeInspectorPanel
        data={null}
        requestState="idle"
      />,
    )

    expect(screen.getByText('sem referência disponível')).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'Tools' }))
    expect(screen.getByText('observabilidade indisponível')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'Logs' }))
    expect(screen.getByText('logs seguros indisponíveis')).toBeInTheDocument()
  })
})

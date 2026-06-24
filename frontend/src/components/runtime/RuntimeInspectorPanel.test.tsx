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

    for (const tab of ['Summary', 'Governance', 'Autonomia', 'Tools', 'Provider', 'Memory', 'OIL', 'Logs']) {
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

  it('renders advisory-only label on Autonomia tab', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_evaluation: {
          decision: 'CONTINUE',
          advisory: true,
          reason: 'No errors.',
          risk_level: 'low',
          session_id: 's1',
          progress_score: 5,
          stagnation_score: 0,
          is_progress: true,
          is_stagnation: false,
          stagnant_attempts: 0,
          fingerprint_id: 'abc123',
          recommended_decision_hint: 'CONTINUE',
          evidence_summary: 'fingerprint=abc123 | progress | progress_score=5',
        },
      },
    }

    render(
      <RuntimeInspectorPanel
        data={normalizeStoredRuntimeMetadata(metadata)}
        requestState="idle"
      />,
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Autonomia' }))

    expect(screen.getByText('Modo somente leitura — nenhuma ação autônoma executada.')).toBeInTheDocument()
    expect(screen.getAllByText('CONTINUE').length).toBeGreaterThanOrEqual(1)
  })

  it('renders tracker scores safely on Autonomia tab', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_evaluation: {
          decision: 'RETRY',
          advisory: true,
          reason: 'Stagnation detected.',
          risk_level: 'low',
          session_id: 's1',
          progress_score: 0,
          stagnation_score: 3,
          is_progress: false,
          is_stagnation: true,
          stagnant_attempts: 2,
          fingerprint_id: 'abc123',
          recommended_decision_hint: 'RETRY',
          evidence_summary: 'fingerprint=abc123 | stagnation | stagnation_score=3',
        },
      },
    }

    render(
      <RuntimeInspectorPanel
        data={normalizeStoredRuntimeMetadata(metadata)}
        requestState="idle"
      />,
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Autonomia' }))

    expect(screen.getByText('Progress Score')).toBeInTheDocument()
    expect(screen.getByText('Stagnation Score')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('Stagnation')).toBeInTheDocument()
    expect(screen.getByText('Evidence')).toBeInTheDocument()
  })

  it('renders evidence summary safely on Autonomia tab', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_evaluation: {
          decision: 'ESCALATE_TO_MISAEL',
          advisory: true,
          reason: 'High stagnation.',
          risk_level: 'high',
          session_id: 's1',
          progress_score: 0,
          stagnation_score: 5,
          is_progress: false,
          is_stagnation: true,
          stagnant_attempts: 3,
          fingerprint_id: 'abc123',
          recommended_decision_hint: 'ESCALATE_TO_MISAEL',
          evidence_summary: 'fingerprint=abc123 | stagnation | escalation | score=5',
        },
      },
    }

    render(
      <RuntimeInspectorPanel
        data={normalizeStoredRuntimeMetadata(metadata)}
        requestState="idle"
      />,
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Autonomia' }))

    expect(screen.getByText('fingerprint=abc123 | stagnation | escalation | score=5')).toBeInTheDocument()
  })

  it('redacts sensitive autonomy reason', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_evaluation: {
          decision: 'CONTINUE',
          advisory: true,
          reason: 'Bearer sk-proj-should-not-render',
          risk_level: 'low',
          session_id: 's1',
          progress_score: 0,
          stagnation_score: 0,
          is_progress: false,
          is_stagnation: false,
          stagnant_attempts: 0,
          fingerprint_id: '',
          recommended_decision_hint: '',
          evidence_summary: '',
        },
      },
    }

    render(
      <RuntimeInspectorPanel
        data={normalizeStoredRuntimeMetadata(metadata)}
        requestState="idle"
      />,
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Autonomia' }))

    expect(document.body.textContent).toContain('[REDACTED]')
    expect(document.body.textContent).not.toContain('should-not-render')
  })

  it('shows empty state on Autonomia tab when no autonomy data', async () => {
    render(
      <RuntimeInspectorPanel
        data={null}
        requestState="idle"
      />,
    )

    await userEvent.click(screen.getByRole('tab', { name: 'Autonomia' }))

    expect(screen.getByText('não disponível')).toBeInTheDocument()
  })

  it('renders detailed token usage in summary and provider tabs', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      usage: { input_tokens: 1_000, output_tokens: 200, total_tokens: 1_200 },
      providerDiagnostics: [{
        provider: 'openai',
        model: 'gpt-test',
        attempted: true,
        succeeded: true,
        tokens_in: 1_000,
        tokens_out: 200,
        total_tokens: 1_200,
      }],
    }

    render(
      <RuntimeInspectorPanel
        data={normalizeStoredRuntimeMetadata(metadata)}
        requestState="idle"
      />,
    )

    expect(screen.getByText('Entrada: 1.000')).toBeInTheDocument()
    expect(screen.getByText('Saída: 200')).toBeInTheDocument()
    expect(screen.getByText('Total: 1.200')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'Provider' }))

    expect(screen.getByText('Entrada: 1.000')).toBeInTheDocument()
    expect(screen.getByText('Saída: 200')).toBeInTheDocument()
    expect(screen.getByText('Total: 1.200')).toBeInTheDocument()
  })
})

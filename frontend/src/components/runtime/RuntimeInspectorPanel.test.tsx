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

    expect(screen.getByText('Diagnóstico somente leitura — nenhuma ação autônoma executada.')).toBeInTheDocument()
    expect(screen.getAllByText('CONTINUE').length).toBeGreaterThanOrEqual(1)
  })

  it('renders process-local autonomy session diagnostics', async () => {
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
          progress_score: 0,
          stagnation_score: 0,
          is_progress: false,
          is_stagnation: false,
          stagnant_attempts: 0,
          fingerprint_id: '',
          recommended_decision_hint: '',
          evidence_summary: '',
          session_state_diagnostics: {
            session_state_source: 'process_local',
            session_state_persistence_enabled: false,
            session_state_hydrated: false,
            session_state_upserted: false,
            session_state_degraded: false,
            session_state_last_error_category: '',
            session_state_updated_at: '2026-06-27T03:00:00+00:00',
            session_state_expires_at: '2026-07-04T03:00:00+00:00',
            session_state_fields_count: 4,
            expired_state_cleanup_supported: false,
            last_cleanup_attempted_at: '',
            last_cleanup_deleted_count: 0,
            cleanup_degraded: false,
            cleanup_last_error_category: '',
            session_state_ttl_seconds: 604800,
            expired_state_count: 0,
          },
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

    expect(screen.getByText('Estado da Sessão')).toBeInTheDocument()
    expect(screen.getByText('Process-local')).toBeInTheDocument()
    expect(screen.getByText('Campos Seguros')).toBeInTheDocument()
    expect(screen.getByText('Cleanup Suportado')).toBeInTheDocument()
    expect(screen.getByText('TTL')).toBeInTheDocument()
    expect(screen.getByText('604800s')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })

  it('renders SQLite hydrated autonomy session diagnostics', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_evaluation: {
          decision: 'RETRY',
          advisory: true,
          reason: 'Stagnation.',
          risk_level: 'low',
          session_id: 's1',
          progress_score: 0,
          stagnation_score: 1,
          is_progress: false,
          is_stagnation: true,
          stagnant_attempts: 1,
          fingerprint_id: 'abc123',
          recommended_decision_hint: 'RETRY',
          evidence_summary: '',
          session_state_diagnostics: {
            session_state_source: 'sqlite_hydrated',
            session_state_persistence_enabled: true,
            session_state_hydrated: true,
            session_state_upserted: true,
            session_state_degraded: false,
            session_state_last_error_category: 'timeout',
            session_state_updated_at: '2026-06-27T03:00:00+00:00',
            session_state_expires_at: '2026-07-04T03:00:00+00:00',
            session_state_fields_count: 8,
            expired_state_cleanup_supported: true,
            last_cleanup_attempted_at: '2026-06-27T04:00:00+00:00',
            last_cleanup_deleted_count: 2,
            cleanup_degraded: false,
            cleanup_last_error_category: '',
            session_state_ttl_seconds: 604800,
            expired_state_count: 0,
          },
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

    expect(screen.getByText('SQLite hidratado')).toBeInTheDocument()
    expect(screen.getByText('Categoria de Erro')).toBeInTheDocument()
    expect(screen.getByText('timeout')).toBeInTheDocument()
    expect(screen.getByText('Estados Removidos')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders SQLite fallback and failure diagnostics safely', async () => {
    const cases = [
      ['sqlite_missing', 'SQLite sem estado salvo'],
      ['sqlite_read_failed', 'Falha de leitura SQLite'],
      ['sqlite_write_failed', 'Falha de gravação SQLite'],
    ] as const

    for (const [source, label] of cases) {
      const metadata: RuntimeMetadata = {
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_evaluation: {
            decision: 'CONTINUE',
            advisory: true,
            reason: 'ok',
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
            session_state_diagnostics: {
              session_state_source: source,
              session_state_persistence_enabled: true,
              session_state_hydrated: false,
              session_state_upserted: source === 'sqlite_missing',
              session_state_degraded: source !== 'sqlite_missing',
              session_state_last_error_category: 'timeout',
              session_state_updated_at: '2026-06-27T03:00:00+00:00',
              session_state_expires_at: '2026-07-04T03:00:00+00:00',
              session_state_fields_count: 5,
              expired_state_cleanup_supported: true,
              last_cleanup_attempted_at: '2026-06-27T04:00:00+00:00',
              last_cleanup_deleted_count: 0,
              cleanup_degraded: source !== 'sqlite_missing',
              cleanup_last_error_category: source === 'sqlite_write_failed' ? 'cleanup_failed' : '',
              session_state_ttl_seconds: 604800,
              expired_state_count: 1,
            },
          },
        },
      }

      const { unmount } = render(
        <RuntimeInspectorPanel
          data={normalizeStoredRuntimeMetadata(metadata)}
          requestState="idle"
        />,
      )

      await userEvent.click(screen.getByRole('tab', { name: 'Autonomia' }))

      expect(screen.getByText(label)).toBeInTheDocument()
      expect(screen.getByText('Degradado com Segurança')).toBeInTheDocument()
      expect(screen.getByText('Estados Expirados')).toBeInTheDocument()
      unmount()
    }
  })

  it('preserves empty session diagnostics when missing', async () => {
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

    expect(screen.getByText('Estado da Sessão')).toBeInTheDocument()
    expect(screen.getByText('Fonte')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('does not render forbidden session diagnostic fields or controls', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_evaluation: {
          decision: 'RETRY',
          advisory: true,
          reason: 'ok',
          risk_level: 'low',
          session_id: 's1',
          progress_score: 0,
          stagnation_score: 1,
          is_progress: false,
          is_stagnation: true,
          stagnant_attempts: 1,
          fingerprint_id: '',
          recommended_decision_hint: 'RETRY',
          evidence_summary: '',
          session_state_diagnostics: {
            session_state_source: 'sqlite_hydrated',
            session_state_persistence_enabled: true,
            session_state_hydrated: true,
            session_state_upserted: true,
            session_state_degraded: false,
            session_state_last_error_category: 'Bearer sk-proj-should-not-render',
            session_state_updated_at: '2026-06-27T03:00:00+00:00',
            session_state_expires_at: '2026-07-04T03:00:00+00:00',
            session_state_fields_count: 8,
            expired_state_cleanup_supported: true,
            cleanup_degraded: true,
            cleanup_last_error_category: 'Bearer sk-proj-cleanup',
            session_state_ttl_seconds: 604800,
            expired_state_count: 3,
            raw_prompt: 'do not render',
            raw_response: 'do not render',
            provider_payload: 'do not render',
          },
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
    expect(document.body.textContent).not.toContain('raw_prompt')
    expect(document.body.textContent).not.toContain('raw_response')
    expect(document.body.textContent).not.toContain('provider_payload')
    expect(screen.queryByRole('button', { name: 'RETRY' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'SELF_REPAIR' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'SWITCH_PROVIDER' })).not.toBeInTheDocument()
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

  it('renders controller stats on Autonomia tab', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_evaluation: {
          decision: 'CONTINUE',
          advisory: true,
          reason: 'All good.',
          risk_level: 'low',
          session_id: 's1',
          progress_score: 5,
          stagnation_score: 0,
          is_progress: true,
          is_stagnation: false,
          stagnant_attempts: 0,
          fingerprint_id: 'abc123',
          recommended_decision_hint: 'CONTINUE',
          evidence_summary: '',
        },
        autonomy_controller_stats: {
          total_evaluations: 10,
          decisions_by_type: { CONTINUE: 7, RETRY: 2, ESCALATE_TO_MISAEL: 1 },
          escalation_count: 1,
          escalation_rate: 0.1,
          abort_safe_count: 0,
          continue_count: 7,
          retry_count: 2,
          replan_count: 0,
          pause_count: 0,
          last_decision: 'CONTINUE',
          last_risk_level: 'low',
          last_updated_at: '2026-06-24T02:49:13Z',
          advisory_mode_enabled: true,
          active_session_count: 2,
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

    expect(screen.getByText('Métricas do Controlador')).toBeInTheDocument()
    expect(screen.getByText('Total de Avaliações')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('10.0%')).toBeInTheDocument()
    expect(screen.getByText('Sim')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders controller stats even without per-turn autonomy data', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_controller_stats: {
          total_evaluations: 3,
          escalation_count: 0,
          escalation_rate: 0,
          abort_safe_count: 0,
          continue_count: 2,
          retry_count: 1,
          replan_count: 0,
          pause_count: 0,
          last_decision: 'CONTINUE',
          last_risk_level: 'low',
          last_updated_at: null,
          advisory_mode_enabled: true,
          active_session_count: 1,
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

    expect(screen.getByText('Métricas do Controlador')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('0.0%')).toBeInTheDocument()
  })

  it('redacts sensitive stats values', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_controller_stats: {
          total_evaluations: 5,
          last_decision: 'Bearer sk-proj-leaked',
          last_risk_level: 'sk-proj-should-not-render',
          escalation_rate: 0.2,
          escalation_count: 1,
          abort_safe_count: 0,
          continue_count: 3,
          retry_count: 1,
          replan_count: 0,
          pause_count: 0,
          active_session_count: 1,
          advisory_mode_enabled: true,
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
    expect(document.body.textContent).not.toContain('sk-proj-leaked')
    expect(document.body.textContent).not.toContain('should-not-render')
  })

  it('renders timeline section on Autonomia tab with empty state', async () => {
    const metadata: RuntimeMetadata = {
      matchedCommands: [],
      matchedTools: [],
      cognitiveRuntimeInspection: {
        autonomy_evaluation: {
          decision: 'CONTINUE',
          advisory: true,
          reason: 'ok',
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

    expect(screen.getByText('Timeline de Decisões')).toBeInTheDocument()
    expect(screen.getByText('Nenhuma decisão de autonomia registrada no histórico.')).toBeInTheDocument()
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

import { describe, expect, it } from 'vitest'
import type { RuntimeMetadata } from '../types'
import {
  normalizeAutonomyTimelineItem,
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
    expect(normalized.autonomy).toBeNull()
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

  describe('autonomy evaluation', () => {
    it('normalizes autonomy evaluation data from inspection', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_evaluation: {
            decision: 'RETRY',
            advisory: true,
            reason: 'Transient error detected: timeout. Advisory retry.',
            risk_level: 'low',
            session_id: 's1',
            progress_score: 0,
            stagnation_score: 1,
            is_progress: false,
            is_stagnation: true,
            stagnant_attempts: 1,
            fingerprint_id: 'abc123def456',
            recommended_decision_hint: 'RETRY',
            evidence_summary: 'fingerprint=abc123def456 | repeated_error | stagnation | progress_score=0 | stagnation_score=1 | stagnant_attempts=1 | distinct_errors=1 | hint=RETRY',
            dry_run_retry_plan: {
              plan_id: 'dry-retry-abc123',
              plan_type: 'dry_run_retry',
              advisory: true,
              would_retry: true,
              retry_reason: 'retry_eligible',
              blocked: false,
              block_reasons: [],
              retry_eligibility_score: 1,
              risk_level: 'low',
              source_decision: 'RETRY',
              fingerprint_id: 'abc123def456',
              stagnation_score: 1,
              progress_score: 0,
              repeated_strategy_count: 0,
              max_attempts_remaining: 1,
              evidence_summary: 'fingerprint=abc123def456 | retry eligible',
              created_at: '2026-06-27T12:00:00Z',
            },
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
              last_cleanup_deleted_count: 1,
              cleanup_degraded: false,
              cleanup_last_error_category: '',
              session_state_ttl_seconds: 604800,
              expired_state_count: 0,
            },
          },
        },
      })

      expect(normalized.autonomy).not.toBeNull()
      expect(normalized.autonomy?.decision).toBe('RETRY')
      expect(normalized.autonomy?.advisory).toBe(true)
      expect(normalized.autonomy?.reason).toBe('Transient error detected: timeout. Advisory retry.')
      expect(normalized.autonomy?.risk_level).toBe('low')
      expect(normalized.autonomy?.session_id).toBe('s1')
      expect(normalized.autonomy?.progress_score).toBe(0)
      expect(normalized.autonomy?.stagnation_score).toBe(1)
      expect(normalized.autonomy?.is_progress).toBe(false)
      expect(normalized.autonomy?.is_stagnation).toBe(true)
      expect(normalized.autonomy?.stagnant_attempts).toBe(1)
      expect(normalized.autonomy?.fingerprint_id).toBe('abc123def456')
      expect(normalized.autonomy?.recommended_decision_hint).toBe('RETRY')
      expect(normalized.autonomy?.evidence_summary).toContain('fingerprint=abc123def456')
      expect(normalized.autonomy?.dry_run_retry_plan).toMatchObject({
        plan_id: 'dry-retry-abc123',
        plan_type: 'dry_run_retry',
        advisory: true,
        would_retry: true,
        retry_reason: 'retry_eligible',
        blocked: false,
        retry_eligibility_score: 1,
        risk_level: 'low',
        source_decision: 'RETRY',
        fingerprint_id: 'abc123def456',
        max_attempts_remaining: 1,
      })
      expect(normalized.autonomy?.session_state_diagnostics).toMatchObject({
        session_state_source: 'sqlite_hydrated',
        session_state_persistence_enabled: true,
        session_state_hydrated: true,
        session_state_upserted: true,
        session_state_degraded: false,
        session_state_last_error_category: 'timeout',
        session_state_fields_count: 8,
        expired_state_cleanup_supported: true,
        last_cleanup_deleted_count: 1,
        cleanup_degraded: false,
        session_state_ttl_seconds: 604800,
        expired_state_count: 0,
      })
    })

    it('returns null autonomy when autonomy_evaluation is missing', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {},
      })

      expect(normalized.autonomy).toBeNull()
    })

    it('redacts sensitive fields in autonomy data', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_evaluation: {
            decision: 'CONTINUE',
            advisory: true,
            reason: 'Bearer sk-proj-leaked',
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
              session_state_source: 'sqlite_hydrated',
              session_state_persistence_enabled: true,
              session_state_hydrated: true,
              session_state_upserted: true,
              session_state_degraded: false,
              session_state_last_error_category: 'Bearer sk-proj-leaked',
              session_state_updated_at: '2026-06-27T03:00:00+00:00',
              session_state_expires_at: '2026-07-04T03:00:00+00:00',
              session_state_fields_count: 8,
              cleanup_last_error_category: 'Bearer sk-proj-cleanup',
              raw_prompt: 'do not normalize',
            },
          },
        },
      })

      expect(normalized.autonomy?.reason).toBe('[REDACTED]')
      expect(normalized.autonomy?.session_state_diagnostics?.session_state_last_error_category).toBe('[REDACTED]')
      expect(normalized.autonomy?.session_state_diagnostics?.cleanup_last_error_category).toBe('Bearer [REDACTED]')
      expect(normalized.autonomy?.session_state_diagnostics).not.toHaveProperty('raw_prompt')
    })

    it('normalizes dry-run retry plan safely', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_evaluation: {
            decision: 'RETRY',
            advisory: true,
            dry_run_retry_plan: {
              plan_id: 'dry-retry-safe',
              plan_type: 'dry_run_retry',
              advisory: true,
              would_retry: false,
              retry_reason: 'retry_blocked',
              blocked: true,
              block_reasons: ['risk_too_high', 'Bearer sk-proj-block'],
              retry_eligibility_score: 0,
              risk_level: 'high',
              source_decision: 'RETRY',
              fingerprint_id: 'fp-safe',
              stagnation_score: 3,
              progress_score: 0,
              repeated_strategy_count: 2,
              max_attempts_remaining: 0,
              evidence_summary: 'Bearer sk-proj-evidence',
              created_at: '2026-06-27T12:00:00Z',
              raw_prompt: 'do not normalize',
              raw_response: 'do not normalize',
            },
          },
        },
      })

      const plan = normalized.autonomy?.dry_run_retry_plan
      expect(plan).toMatchObject({
        plan_id: 'dry-retry-safe',
        plan_type: 'dry_run_retry',
        advisory: true,
        would_retry: false,
        retry_reason: 'retry_blocked',
        blocked: true,
        retry_eligibility_score: 0,
        risk_level: 'high',
        source_decision: 'RETRY',
        fingerprint_id: 'fp-safe',
        stagnation_score: 3,
        progress_score: 0,
        repeated_strategy_count: 2,
        max_attempts_remaining: 0,
        created_at: '2026-06-27T12:00:00Z',
      })
      expect(plan?.block_reasons).toEqual(['risk_too_high', '[REDACTED]'])
      expect(plan?.evidence_summary).toBe('Bearer [REDACTED]')
      expect(plan).not.toHaveProperty('raw_prompt')
      expect(plan).not.toHaveProperty('raw_response')
    })

    it('preserves empty dry-run retry plan state when missing', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_evaluation: {
            decision: 'CONTINUE',
            advisory: true,
          },
        },
      })

      expect(normalized.autonomy?.dry_run_retry_plan).toBeNull()
    })

    it('drops unknown autonomy session state diagnostic source', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_evaluation: {
            decision: 'CONTINUE',
            advisory: true,
            session_state_diagnostics: {
              session_state_source: 'raw_response',
              session_state_persistence_enabled: true,
              session_state_hydrated: false,
              session_state_upserted: false,
              session_state_degraded: true,
              session_state_fields_count: 2,
            },
          },
        },
      })

      expect(normalized.autonomy?.session_state_diagnostics?.session_state_source).toBeNull()
      expect(normalized.autonomy?.session_state_diagnostics?.session_state_degraded).toBe(true)
    })

    it('handles null autonomy_evaluation gracefully', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_evaluation: null,
        },
      })

      expect(normalized.autonomy).toBeNull()
    })
  })

  describe('autonomy controller stats', () => {
    it('normalizes controller stats from inspection', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
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
      })

      expect(normalized.autonomy_stats).not.toBeNull()
      expect(normalized.autonomy_stats?.total_evaluations).toBe(10)
      expect(normalized.autonomy_stats?.decisions_by_type).toEqual({ CONTINUE: 7, RETRY: 2, ESCALATE_TO_MISAEL: 1 })
      expect(normalized.autonomy_stats?.escalation_count).toBe(1)
      expect(normalized.autonomy_stats?.escalation_rate).toBe(0.1)
      expect(normalized.autonomy_stats?.abort_safe_count).toBe(0)
      expect(normalized.autonomy_stats?.continue_count).toBe(7)
      expect(normalized.autonomy_stats?.retry_count).toBe(2)
      expect(normalized.autonomy_stats?.last_decision).toBe('CONTINUE')
      expect(normalized.autonomy_stats?.last_risk_level).toBe('low')
      expect(normalized.autonomy_stats?.last_updated_at).toBe('2026-06-24T02:49:13Z')
      expect(normalized.autonomy_stats?.advisory_mode_enabled).toBe(true)
      expect(normalized.autonomy_stats?.active_session_count).toBe(2)
    })

    it('returns null when stats are missing', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {},
      })

      expect(normalized.autonomy_stats).toBeNull()
    })

    it('handles malformed stats gracefully', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_controller_stats: 'not-a-record',
        },
      })

      expect(normalized.autonomy_stats).toBeNull()
    })

    it('redacts sensitive fields in stats', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_controller_stats: {
            total_evaluations: 5,
            last_decision: 'Bearer sk-proj-leaked-decision',
            last_risk_level: 'sk-proj-leaked-risk',
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
      })

      expect(normalized.autonomy_stats?.total_evaluations).toBe(5)
      expect(normalized.autonomy_stats?.last_decision).toBe('Bearer [REDACTED]')
      expect(normalized.autonomy_stats?.last_risk_level).toBe('[REDACTED]')
    })

    it('filters non-numeric values from decisions_by_type', () => {
      const normalized = normalizeRuntimeInspectorData({
        matchedCommands: [],
        matchedTools: [],
        cognitiveRuntimeInspection: {
          autonomy_controller_stats: {
            total_evaluations: 5,
            decisions_by_type: { CONTINUE: 3, RETRY: 'invalid' },
            escalation_count: 1,
            escalation_rate: 0.2,
            abort_safe_count: 0,
            continue_count: 3,
            retry_count: 1,
            replan_count: 0,
            pause_count: 0,
            active_session_count: 1,
            advisory_mode_enabled: true,
          },
        },
      })

      expect(normalized.autonomy_stats?.decisions_by_type).toEqual({ CONTINUE: 3 })
      expect(normalized.autonomy_stats?.decisions_by_type?.RETRY).toBeUndefined()
    })

    it('preserves empty state when only per-turn data present', () => {
      const normalized = normalizeRuntimeInspectorData({
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
      })

      expect(normalized.autonomy).not.toBeNull()
      expect(normalized.autonomy_stats).toBeNull()
    })
  })

  describe('normalizeAutonomyTimelineItem', () => {
    it('returns null for non-object value', () => {
      expect(normalizeAutonomyTimelineItem(null, 'm1', 's1', '2026-06-24T00:00:00Z')).toBeNull()
      expect(normalizeAutonomyTimelineItem('invalid', 'm1', 's1', '2026-06-24T00:00:00Z')).toBeNull()
      expect(normalizeAutonomyTimelineItem(42, 'm1', 's1', '2026-06-24T00:00:00Z')).toBeNull()
    })

    it('returns null when decision is missing or empty', () => {
      expect(normalizeAutonomyTimelineItem({ advisory: true }, 'm1', 's1', '2026-06-24T00:00:00Z')).toBeNull()
      expect(normalizeAutonomyTimelineItem({ decision: '' }, 'm1', 's1', '2026-06-24T00:00:00Z')).toBeNull()
    })

    it('normalizes a valid timeline item with all fields', () => {
      const item = normalizeAutonomyTimelineItem(
        {
          decision: 'RETRY',
          advisory: true,
          risk_level: 'medium',
          fingerprint_id: 'fp-123',
          progress_score: 2,
          stagnation_score: 4,
          is_progress: false,
          is_stagnation: true,
          stagnant_attempts: 2,
          recommended_decision_hint: 'RETRY',
          evidence_summary: 'stagnation detected',
          strategies_attempted: ['retry_provider', 'switch_tool'],
          repeated_strategy_count: 1,
        },
        'msg-1',
        'session-abc',
        '2026-06-24T12:30:00Z',
      )

      expect(item).not.toBeNull()
      expect(item!.id).toBe('msg-1')
      expect(item!.session_id).toBe('session-abc')
      expect(item!.decision).toBe('RETRY')
      expect(item!.advisory).toBe(true)
      expect(item!.risk_level).toBe('medium')
      expect(item!.fingerprint_id).toBe('fp-123')
      expect(item!.progress_score).toBe(2)
      expect(item!.stagnation_score).toBe(4)
      expect(item!.is_progress).toBe(false)
      expect(item!.is_stagnation).toBe(true)
      expect(item!.stagnant_attempts).toBe(2)
      expect(item!.recommended_decision_hint).toBe('RETRY')
      expect(item!.evidence_summary).toBe('stagnation detected')
      expect(item!.strategies_attempted).toEqual(['retry_provider', 'switch_tool'])
      expect(item!.repeated_strategy_count).toBe(1)
      expect(item!.timestamp).toBe('2026-06-24T12:30:00Z')
    })

    it('filters non-string values from strategies_attempted', () => {
      const item = normalizeAutonomyTimelineItem(
        {
          decision: 'CONTINUE',
          strategies_attempted: ['strategy_a', 42, null, 'strategy_b'],
        },
        'm1',
        's1',
        '2026-06-24T00:00:00Z',
      )

      expect(item!.strategies_attempted).toEqual(['strategy_a', 'strategy_b'])
    })

    it('returns safe string for missing or null optional fields', () => {
      const item = normalizeAutonomyTimelineItem(
        { decision: 'CONTINUE' },
        'm1',
        's1',
        '2026-06-24T00:00:00Z',
      )

      expect(item!.risk_level).toBeNull()
      expect(item!.fingerprint_id).toBeNull()
      expect(item!.progress_score).toBeNull()
      expect(item!.stagnation_score).toBeNull()
      expect(item!.is_progress).toBeNull()
      expect(item!.is_stagnation).toBeNull()
      expect(item!.stagnant_attempts).toBeNull()
      expect(item!.recommended_decision_hint).toBeNull()
      expect(item!.evidence_summary).toBeNull()
      expect(item!.repeated_strategy_count).toBeNull()
      expect(item!.strategies_attempted).toEqual([])
    })
  })
})

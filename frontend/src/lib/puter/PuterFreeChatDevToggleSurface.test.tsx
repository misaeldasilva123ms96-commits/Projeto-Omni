import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import {
  PUTER_FREE_CHAT_DEV_TOGGLE_VERSION,
  PuterFreeChatDevToggleSurface,
  createPuterFreeChatDevToggleState,
  isPuterFreeChatDevToggleFlagEnabled,
  resultToPuterFreeChatDevToggleState,
} from './PuterFreeChatDevToggleSurface'

const FORBIDDEN_FRAGMENTS = [
  'access_token',
  'api_key',
  'billing',
  'credential',
  'debug',
  'env',
  'private_endpoint',
  'provider_config',
  'provider_payload',
  'raw_provider',
  'request_payload',
  'secret',
  'sk-',
  'stack',
  'traceback',
]

function safeEnvelope(overrides: Record<string, unknown> = {}) {
  return {
    ok: true,
    access_snapshot: {
      snapshot_version: 'public_access_snapshot_v1',
      plan_mode: 'free',
      provider_mode: 'experimental_free',
      subject_id: 'session-1',
      usage_date: '2026-05-24',
      tokens_in: 100,
      tokens_out: 25,
      tokens_total: 125,
      daily_token_limit: 15000,
      quota_remaining: 14875,
      quota_exceeded: false,
      input_allowed: true,
      output_allowed: true,
      quota_allowed: true,
      routing_allowed: true,
      fallback_allowed: false,
      selected_provider_family: 'experimental_free_provider',
      selected_adapter_id: 'experimental_free_adapter',
      adapter_display_name: 'Experimental Free Provider',
      adapter_capabilities: {
        supports_streaming: false,
        supports_tools: false,
        supports_files: false,
        supports_long_context: false,
        supports_sensitive_tools: false,
        is_experimental: true,
        is_user_key_required: false,
        is_managed: false,
        is_internal: false,
      },
      decision_reason: 'routing_allowed',
    },
    denied: false,
    reason: 'ok',
    snapshot_version: 'public_access_snapshot_v1',
    boundary_version: 'access_snapshot_boundary_v1',
    ...overrides,
  }
}

function deniedEnvelope(reason = 'quota_exceeded') {
  const envelope = safeEnvelope({
    ok: false,
    denied: true,
    reason,
  })

  return {
    ...envelope,
    access_snapshot: {
      ...(envelope.access_snapshot as Record<string, unknown>),
      routing_allowed: false,
      fallback_allowed: true,
      decision_reason: reason,
    },
  }
}

function puterRuntime(chat = vi.fn().mockResolvedValue('safe dev chat response')) {
  return {
    window: {
      puter: {
        ai: {
          chat,
        },
      },
    },
  }
}

function renderEnabled(chat = vi.fn().mockResolvedValue('safe dev chat response'), envelope: unknown = safeEnvelope()) {
  render(
    <PuterFreeChatDevToggleSurface
      accessSnapshotEnvelope={envelope}
      chatBridgeFeatureEnabled
      chatDevToggleEnabled
      defaultPrompt="Safe dev chat prompt"
      devRealFeatureEnabled
      experimentalFeatureEnabled
      runtime={puterRuntime(chat)}
    />,
  )
}

function expectPublicSafeText(value: string | null | undefined) {
  const text = String(value ?? '').toLowerCase()
  for (const fragment of FORBIDDEN_FRAGMENTS) {
    expect(text).not.toContain(fragment)
  }
}

describe('Puter Free chat dev toggle surface', () => {
  it('keeps the dev chat toggle flag disabled unless explicitly enabled', () => {
    expect(isPuterFreeChatDevToggleFlagEnabled()).toBe(false)
    expect(isPuterFreeChatDevToggleFlagEnabled('')).toBe(false)
    expect(isPuterFreeChatDevToggleFlagEnabled('false')).toBe(false)
    expect(isPuterFreeChatDevToggleFlagEnabled('true')).toBe(true)
    expect(isPuterFreeChatDevToggleFlagEnabled('1')).toBe(true)
  })

  it('creates exact safe state objects', () => {
    expect(createPuterFreeChatDevToggleState()).toEqual({
      toggle_version: PUTER_FREE_CHAT_DEV_TOGGLE_VERSION,
      active: false,
      denied: true,
      pending: false,
      reason: 'not_invoked',
      provider_family: 'experimental_free_provider',
      adapter_id: '',
      sanitized_text: '',
      experimental: true,
    })
  })

  it('does not render unless every required flag is enabled', () => {
    for (const props of [
      {},
      { experimentalFeatureEnabled: true },
      { experimentalFeatureEnabled: true, chatBridgeFeatureEnabled: true },
      { experimentalFeatureEnabled: true, chatBridgeFeatureEnabled: true, devRealFeatureEnabled: true },
    ]) {
      const { unmount } = render(
        <PuterFreeChatDevToggleSurface
          accessSnapshotEnvelope={safeEnvelope()}
          runtime={puterRuntime()}
          {...props}
        />,
      )
      expect(screen.queryByLabelText('Puter Free chat dev toggle')).toBeNull()
      unmount()
    }

    render(
      <PuterFreeChatDevToggleSurface
        accessSnapshotEnvelope={safeEnvelope()}
        chatBridgeFeatureEnabled
        chatDevToggleEnabled
        devRealFeatureEnabled
        experimentalFeatureEnabled
        runtime={puterRuntime()}
      />,
    )
    expect(screen.getByLabelText('Puter Free chat dev toggle')).toBeInTheDocument()
  })

  it('does not call Puter on import, render, or mount', async () => {
    const chat = vi.fn()
    ;(globalThis as typeof globalThis & { puter?: unknown }).puter = { ai: { chat } }

    await import('./PuterFreeChatDevToggleSurface')
    renderEnabled(chat)

    expect(chat).not.toHaveBeenCalled()
    delete (globalThis as typeof globalThis & { puter?: unknown }).puter
  })

  it('requires a manual action before invoking the dev-real bridge', async () => {
    const user = userEvent.setup()
    const chat = vi.fn().mockResolvedValue('safe dev chat response')

    renderEnabled(chat)
    expect(chat).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Run dev Free chat bridge' }))

    await waitFor(() => expect(chat).toHaveBeenCalledTimes(1))
    expect(chat).toHaveBeenCalledWith('Safe dev chat prompt')
    expect(screen.getByLabelText('Puter Free chat dev result')).toHaveTextContent('safe dev chat response')
  })

  it('does not call Puter when boundary state is denied', async () => {
    const user = userEvent.setup()
    const chat = vi.fn()

    renderEnabled(chat, deniedEnvelope('quota_exceeded'))
    await user.click(screen.getByRole('button', { name: 'Run dev Free chat bridge' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter Free chat dev result')).toHaveTextContent('routing_denied')
    })
    expect(chat).not.toHaveBeenCalled()
    expectPublicSafeText(screen.getByLabelText('Puter Free chat dev result').textContent)
  })

  it('does not call Puter when runtime is missing', async () => {
    const user = userEvent.setup()

    render(
      <PuterFreeChatDevToggleSurface
        accessSnapshotEnvelope={safeEnvelope()}
        chatBridgeFeatureEnabled
        chatDevToggleEnabled
        defaultPrompt="Safe dev chat prompt"
        devRealFeatureEnabled
        experimentalFeatureEnabled
        runtime={{ window: {} }}
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Run dev Free chat bridge' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter Free chat dev result')).toHaveTextContent('puter_runtime_unavailable')
    })
  })

  it('shows sanitized output and never raw provider payload text', async () => {
    const user = userEvent.setup()
    const chat = vi.fn().mockResolvedValue({
      text: 'visible dev answer sk-proj-abcdefghijkl user@example.com',
      raw_provider_payload: { text: 'raw hidden dev value' },
    })

    renderEnabled(chat)
    await user.click(screen.getByRole('button', { name: 'Run dev Free chat bridge' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Puter Free chat dev result')).toHaveTextContent(
        'visible dev answer [redacted] [redacted]',
      )
    })
    expect(screen.getByLabelText('Puter Free chat dev result')).not.toHaveTextContent('raw hidden dev value')
    expectPublicSafeText(screen.getByLabelText('Puter Free chat dev result').textContent)
  })

  it('converts bridge results into safe UI state', () => {
    const state = resultToPuterFreeChatDevToggleState({
      dev_real_bridge_version: 'free_mode_chat_bridge_dev_real_v1',
      allowed: true,
      denied: false,
      reason: 'ok',
      dev_real_enabled: true,
      provider_family: 'experimental_free_provider',
      adapter_id: 'puter_browser_skeleton_adapter',
      fallback_required: false,
      sanitized_output: 'safe text',
      runtime_truth: {
        access_layer_plan_mode: 'free',
        provider_family: 'experimental_free_provider',
        provider_attempted: true,
        provider_succeeded: true,
        provider_failed_reason: '',
        fallback_triggered: false,
        quota_allowed: true,
        quota_exceeded: false,
        routing_allowed: true,
        selected_adapter_id: 'experimental_free_adapter',
        boundary_version: 'access_snapshot_boundary_v1',
        snapshot_version: 'public_access_snapshot_v1',
        sanitized_output: 'safe text',
      },
    })

    expect(state).toMatchObject({
      active: true,
      denied: false,
      reason: 'ok',
      adapter_id: 'puter_browser_skeleton_adapter',
      sanitized_text: 'safe text',
    })
  })

  it('does not expose override controls or direct provider/network execution paths', async () => {
    renderEnabled()

    const surfaceText = screen.getByLabelText('Puter Free chat dev toggle').textContent?.toLowerCase() ?? ''
    for (const fragment of [
      'provider_mode',
      'provider_family',
      'adapter_id',
      'selected_adapter_id',
      'policy_overrides',
      'billing',
      'debug',
      'tools',
      'files',
      'function',
    ]) {
      expect(surfaceText).not.toContain(fragment)
    }

    const source = await import('./PuterFreeChatDevToggleSurface?raw')
    const lowered = source.default.toLowerCase()
    expect(lowered).not.toContain('sendomnimessage')
    expect(lowered).not.toContain('chatapi')
    expect(lowered).not.toContain('puter.ai.chat')
    expect(lowered).not.toContain('fetch(')
    expect(lowered).not.toContain('xmlhttprequest')
    expect(lowered).not.toContain('navigator.sendbeacon')
    expect(lowered).not.toContain('websocket')
  })
})

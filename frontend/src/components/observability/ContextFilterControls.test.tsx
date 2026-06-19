import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ObservabilityContext } from '../../lib/observabilityContext'
import { ContextFilterControls } from './ContextFilterControls'

describe('ContextFilterControls', () => {
  const writeText = vi.fn()

  beforeEach(() => {
    window.history.replaceState({}, '', '/observability')
    writeText.mockReset()
    writeText.mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
  })

  it('renders chips only for sanitized allowlisted context', () => {
    render(
      <ContextFilterControls
        context={{
          trace_id: 'trace-safe',
          runtime_mode: 'FULL_COGNITIVE_RUNTIME',
          token: 'secret',
          payload: 'raw',
        } as ObservabilityContext}
        overviewPath="/observability"
      />,
    )

    expect(screen.getByText('trace_id: trace-safe')).toBeInTheDocument()
    expect(screen.getByText('runtime_mode: FULL_COGNITIVE_RUNTIME')).toBeInTheDocument()
    expect(screen.queryByText(/secret|payload|token|raw/i)).not.toBeInTheDocument()
  })

  it('clears contextual query parameters from the URL', () => {
    window.history.replaceState(
      {},
      '',
      '/observability?trace_id=trace-safe&token=secret',
    )
    render(
      <ContextFilterControls
        context={{ trace_id: 'trace-safe' }}
        navigate={(path) => window.history.replaceState({}, '', path)}
        overviewPath="/observability"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Limpar filtros' }))

    expect(window.location.pathname).toBe('/observability')
    expect(window.location.search).toBe('')
  })

  it('copies only the sanitized allowlisted reference', async () => {
    render(
      <ContextFilterControls
        context={{
          trace_id: 'trace-safe',
          provider: 'openai',
          token: 'secret',
        } as ObservabilityContext}
        overviewPath="/observability"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Copiar referência' }))

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        '/observability?trace_id=trace-safe&provider=openai',
      )
    })
  })

  it('does not crash when the Clipboard API is unavailable', () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
    })
    render(
      <ContextFilterControls
        context={{ trace_id: 'trace-safe' }}
        overviewPath="/observability"
      />,
    )

    expect(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Copiar referência' }))
    }).not.toThrow()
  })

  it('navigates back to the unfiltered overview', () => {
    window.history.replaceState({}, '', '/observability?trace_id=trace-safe')
    render(
      <ContextFilterControls
        context={{ trace_id: 'trace-safe' }}
        navigate={(path) => window.history.pushState({}, '', path)}
        overviewPath="/observability"
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Voltar para visão geral' }))

    expect(window.location.pathname).toBe('/observability')
    expect(window.location.search).toBe('')
  })

  it('renders nothing without safe context', () => {
    const { container } = render(
      <ContextFilterControls context={{}} overviewPath="/observability" />,
    )

    expect(container).toBeEmptyDOMElement()
  })
})

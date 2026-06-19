import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ObservabilityContextBanner } from './ObservabilityContextBanner'

describe('ObservabilityContextBanner', () => {
  it('renders safe contextual values', () => {
    render(
      <ObservabilityContextBanner
        context={{
          trace_id: 'trace-safe',
          runtime_mode: 'FULL_COGNITIVE_RUNTIME',
        }}
      />,
    )

    expect(screen.getByText('Contexto do Runtime Inspector')).toBeInTheDocument()
    expect(screen.getByText('trace_id: trace-safe')).toBeInTheDocument()
    expect(screen.getByText('runtime_mode: FULL_COGNITIVE_RUNTIME')).toBeInTheDocument()
  })

  it('renders nothing without context', () => {
    const { container } = render(<ObservabilityContextBanner context={{}} />)

    expect(container).toBeEmptyDOMElement()
  })
})

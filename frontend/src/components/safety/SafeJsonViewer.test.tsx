import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SafeJsonViewer } from './SafeJsonViewer'

describe('SafeJsonViewer', () => {
  it('renders secret-like fields only through the redaction layer', () => {
    render(
      <SafeJsonViewer
        data={{
          trace_id: 'trace-safe',
          authorization: 'Bearer should-not-render',
          nested: { api_key: 'sk-proj-should-not-render' },
        }}
      />,
    )

    expect(screen.getByText('trace-safe', { exact: false })).toBeInTheDocument()
    expect(screen.getAllByText('"[REDACTED]"').length).toBeGreaterThan(0)
    expect(document.body.textContent).not.toContain('should-not-render')
    expect(document.body.textContent).not.toContain('authorization')
    expect(document.body.textContent).not.toContain('api_key')
  })

  it('does not crash on cyclic or malformed payloads', () => {
    const cyclic: Record<string, unknown> = { trace_id: 'trace-safe' }
    cyclic.self = cyclic
    Object.defineProperty(cyclic, 'headers', {
      enumerable: true,
      get() {
        throw new Error('Bearer should-not-render')
      },
    })

    expect(() => render(<SafeJsonViewer data={cyclic} />)).not.toThrow()
    expect(document.body.textContent).toContain('trace-safe')
    expect(document.body.textContent).toContain('[REDACTED]')
    expect(document.body.textContent).not.toContain('should-not-render')
  })
})

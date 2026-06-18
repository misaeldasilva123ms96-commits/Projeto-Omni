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
})

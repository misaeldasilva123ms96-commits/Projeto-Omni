import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

function BrokenSurface() {
  throw new Error('Bearer abcdefghijklmnopqrstuvwxyz')
  return null
}

describe('ErrorBoundary', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('redacts errors in the fallback UI and console', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <BrokenSurface />
      </ErrorBoundary>,
    )

    expect(screen.getByText('[REDACTED]')).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('abcdefghijklmnopqrstuvwxyz')
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain('abcdefghijklmnopqrstuvwxyz')
  })
})

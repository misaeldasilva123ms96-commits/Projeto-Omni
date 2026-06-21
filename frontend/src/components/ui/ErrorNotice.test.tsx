import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ErrorNotice } from './ErrorNotice'

describe('ErrorNotice', () => {
  it('redacts and truncates unsafe error text before rendering', () => {
    render(
      <ErrorNotice
        message={`Request failed: Bearer abcdefghijklmnopqrstuvwxyz ${'detail '.repeat(1000)}`}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('[REDACTED]')
    expect(screen.getByRole('alert')).toHaveTextContent('[TRUNCATED]')
    expect(document.body.textContent).not.toContain('abcdefghijklmnopqrstuvwxyz')
  })
})

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { Layout } from './Layout'

describe('Layout responsive shell', () => {
  it('exposes mobile/tablet tabs and switches visible panel state', async () => {
    render(
      <Layout
        center={<div>Chat content</div>}
        right={<div>Runtime content</div>}
        sidebar={<div>Tools content</div>}
      />,
    )

    expect(screen.getByRole('button', { name: 'Chat' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Runtime' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tools' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Runtime' }))
    expect(screen.getByText('Runtime content').closest('aside')?.className).toContain('block')

    await userEvent.click(screen.getByRole('button', { name: 'Tools' }))
    expect(screen.getByText('Tools content').closest('aside')?.className).toContain('block')
  })
})

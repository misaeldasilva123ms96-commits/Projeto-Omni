import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OmniRightInspector } from './OmniRightInspector'

describe('OmniRightInspector', () => {
  it('renders children when open by default', () => {
    render(<OmniRightInspector><div>Inspector content</div></OmniRightInspector>)
    expect(screen.getByText('Inspector content')).toBeInTheDocument()
  })

  it('renders collapsed button when defaultOpen is false', () => {
    render(<OmniRightInspector defaultOpen={false}><div>Content</div></OmniRightInspector>)
    expect(screen.getByRole('button', { name: /open inspector/i })).toBeInTheDocument()
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('toggles open/closed on button click', async () => {
    render(<OmniRightInspector defaultOpen={false}><div>Content</div></OmniRightInspector>)
    await userEvent.click(screen.getByRole('button', { name: /open inspector/i }))
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('has aria-expanded on toggle button', () => {
    render(<OmniRightInspector defaultOpen={true}><div>Content</div></OmniRightInspector>)
    expect(screen.getByRole('button', { name: /close inspector/i })).toHaveAttribute('aria-expanded', 'true')
  })

  it('has panel region with aria-label', () => {
    render(<OmniRightInspector><div>Content</div></OmniRightInspector>)
    expect(screen.getByRole('region', { name: /inspector panel/i })).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <OmniRightInspector className="custom-class"><div>Content</div></OmniRightInspector>,
    )
    expect(container.querySelector('.custom-class')).toBeInTheDocument()
  })
})

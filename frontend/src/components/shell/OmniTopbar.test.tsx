import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OmniTopbar } from './OmniTopbar'

describe('OmniTopbar', () => {
  it('renders RuntimeTruthBar when no children provided', () => {
    const { container } = render(<OmniTopbar />)
    expect(container.querySelector('header')).toBeInTheDocument()
  })

  it('renders children instead of default content', () => {
    render(<OmniTopbar><span>Custom content</span></OmniTopbar>)
    expect(screen.getByText('Custom content')).toBeInTheDocument()
  })

  it('has header landmark with aria-label', () => {
    render(<OmniTopbar />)
    expect(screen.getByRole('banner')).toHaveAttribute('aria-label', 'Application header')
  })

  it('applies custom className', () => {
    const { container } = render(<OmniTopbar className="custom-class" />)
    expect(container.querySelector('header')?.className).toContain('custom-class')
  })
})

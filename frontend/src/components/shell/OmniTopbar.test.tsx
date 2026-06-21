import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useRuntimeConsoleStore } from '../../state/runtimeConsoleStore'
import { OmniTopbar } from './OmniTopbar'

describe('OmniTopbar', () => {
  it('renders RuntimeTruthBar when no children provided', () => {
    useRuntimeConsoleStore.getState().setRuntimeMetadata(null)
    const { container } = render(<OmniTopbar />)
    expect(container.querySelector('header')).toBeInTheDocument()
    expect(screen.getByText('Tokens indisponíveis')).toBeInTheDocument()
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

  it('shows compact token usage from the latest runtime metadata', () => {
    useRuntimeConsoleStore.getState().setRuntimeMetadata({
      matchedCommands: [],
      matchedTools: [],
      usage: { input_tokens: 1_000, output_tokens: 200 },
    })

    render(<OmniTopbar />)

    expect(screen.getByText('Tokens: 1.2k')).toBeInTheDocument()
  })

  it('uses normalized provider diagnostics when top-level usage is unavailable', () => {
    useRuntimeConsoleStore.getState().setRuntimeMetadata({
      matchedCommands: [],
      matchedTools: [],
      providerDiagnostics: [{
        provider: 'openai',
        selected: true,
        tokens_in: 600,
        tokens_out: 400,
      }],
    })

    render(<OmniTopbar />)

    expect(screen.getByText('Tokens: 1k')).toBeInTheDocument()
  })
})

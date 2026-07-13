import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { OmniShell } from './OmniShell'

describe('OmniShell', () => {
  it('renders children in main content area', () => {
    render(<OmniShell><div>Main content</div></OmniShell>)
    expect(screen.getByText('Main content')).toBeInTheDocument()
  })

  it('has skip-to-content link', () => {
    render(<OmniShell><div>Content</div></OmniShell>)
    const skipLink = screen.getByText('Skip to main content')
    expect(skipLink).toHaveAttribute('href', '#main-content')
  })

  it('main element has role=main and id=main-content', () => {
    render(<OmniShell><div>Content</div></OmniShell>)
    const main = screen.getByRole('main')
    expect(main).toHaveAttribute('id', 'main-content')
  })

  it('renders OmniTopbar', () => {
    render(<OmniShell topbar={<div>Custom topbar</div>}><div>Content</div></OmniShell>)
    expect(screen.getByText('Custom topbar')).toBeInTheDocument()
  })

  it('hides sidebar when showSidebar is false', () => {
    const { container } = render(
      <OmniShell sidebar={<div>Sidebar</div>} showSidebar={false}><div>Content</div></OmniShell>,
    )
    expect(container.querySelector('[aria-label="Sidebar"]')).not.toBeInTheDocument()
  })

  it('hides right panel when showRightPanel is false', () => {
    const { container } = render(
      <OmniShell rightPanel={<div>Inspector</div>} showRightPanel={false}><div>Content</div></OmniShell>,
    )
    expect(container.querySelector('[aria-label="Runtime inspector"]')).not.toBeInTheDocument()
  })

  it('renders sidebar with navigation role when present', () => {
    render(<OmniShell sidebar={<div>Sidebar</div>}><div>Content</div></OmniShell>)
    expect(screen.getByRole('navigation', { name: /sidebar/i })).toBeInTheDocument()
  })

  it('owns the sidebar collapse state', async () => {
    render(<OmniShell sidebar={<div>Sidebar</div>}><div>Content</div></OmniShell>)

    await userEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }))
    expect(screen.getByRole('button', { name: /expand sidebar/i })).toBeInTheDocument()
    expect(screen.queryByText('Sidebar')).not.toBeInTheDocument()
  })

  it('renders inspector with region role when present', () => {
    render(
      <OmniShell rightPanel={<div>Inspector</div>} showRightPanel={true}><div>Content</div></OmniShell>,
    )
    expect(screen.getByRole('region', { name: /runtime inspector/i })).toBeInTheDocument()
  })

  it('renders mobile nav when sidebar or inspector are present', () => {
    render(
      <OmniShell sidebar={<div>Sidebar</div>} showRightPanel={true} rightPanel={<div>Inspector</div>}>
        <div>Content</div>
      </OmniShell>,
    )
    expect(screen.getByRole('tablist')).toBeInTheDocument()
  })

  it('closes an open mobile drawer with Escape', async () => {
    render(<OmniShell sidebar={<div>Sidebar content</div>}><div>Content</div></OmniShell>)
    await userEvent.click(screen.getByRole('tab', { name: /menu/i }))
    expect(screen.getByText('Sidebar content')).toBeVisible()
    await userEvent.keyboard('{Escape}')
    expect(screen.getByRole('tab', { name: /chat/i })).toHaveAttribute('aria-selected', 'true')
  })
})

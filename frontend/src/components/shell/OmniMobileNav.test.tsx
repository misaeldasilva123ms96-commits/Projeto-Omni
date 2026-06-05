import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OmniMobileNav } from './OmniMobileNav'

describe('OmniMobileNav', () => {
  it('renders nothing when only one panel is visible', () => {
    const { container } = render(
      <OmniMobileNav activePanel="content" onSelect={vi.fn()} hasSidebar={false} hasRightPanel={false} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders two buttons when sidebar is visible but not right panel', () => {
    render(
      <OmniMobileNav activePanel="sidebar" onSelect={vi.fn()} hasSidebar={true} hasRightPanel={false} />,
    )
    expect(screen.getByRole('tab', { name: /menu/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /chat/i })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /runtime/i })).not.toBeInTheDocument()
  })

  it('renders three buttons when both panels are visible', () => {
    render(
      <OmniMobileNav activePanel="content" onSelect={vi.fn()} hasSidebar={true} hasRightPanel={true} />,
    )
    expect(screen.getByRole('tab', { name: /menu/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /chat/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /runtime/i })).toBeInTheDocument()
  })

  it('calls onSelect with the correct panel id on click', async () => {
    const onSelect = vi.fn()
    render(
      <OmniMobileNav activePanel="content" onSelect={onSelect} hasSidebar={true} hasRightPanel={true} />,
    )
    await userEvent.click(screen.getByRole('tab', { name: /runtime/i }))
    expect(onSelect).toHaveBeenCalledWith('inspector')
  })

  it('marks the active tab as selected', () => {
    render(
      <OmniMobileNav activePanel="sidebar" onSelect={vi.fn()} hasSidebar={true} hasRightPanel={true} />,
    )
    const menuTab = screen.getByRole('tab', { name: /menu/i })
    expect(menuTab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: /chat/i })).toHaveAttribute('aria-selected', 'false')
  })

  it('uses tablist role and aria-label on container', () => {
    render(
      <OmniMobileNav activePanel="content" onSelect={vi.fn()} hasSidebar={true} hasRightPanel={true} />,
    )
    const tablist = screen.getByRole('tablist')
    expect(tablist).toHaveAttribute('aria-label', 'Panel navigation')
  })
})

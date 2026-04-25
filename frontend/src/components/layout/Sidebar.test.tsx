import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useRuntimeConsoleStore } from '../../state/runtimeConsoleStore'
import { Sidebar } from './Sidebar'

function renderSidebar() {
  return render(
    <Sidebar
      conversations={[]}
      mode="chat"
      onChangeMode={vi.fn()}
      onNewConversation={vi.fn()}
      onSelectView={vi.fn()}
      onSidebarItemSelected={vi.fn()}
      view="chat"
    />,
  )
}

describe('Sidebar', () => {
  beforeEach(() => {
    useRuntimeConsoleStore.getState().resetConversation()
    useRuntimeConsoleStore.getState().clearUiNotice()
  })

  it('navigation updates central state', async () => {
    renderSidebar()
    await userEvent.click(screen.getByRole('button', { name: /Memória/i }))
    expect(useRuntimeConsoleStore.getState().activeSidebarItem).toBe('memoria')
    expect(useRuntimeConsoleStore.getState().panelView).toBe('memory')
  })

  it('active item reflects UI state', async () => {
    renderSidebar()
    const memory = screen.getByRole('button', { name: /Memória/i })
    await userEvent.click(memory)
    expect(memory.className).toContain('text-white')
  })
})

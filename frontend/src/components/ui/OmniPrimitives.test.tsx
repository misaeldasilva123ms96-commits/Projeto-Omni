import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import {
  OmniBadge,
  OmniButton,
  OmniCard,
  OmniInput,
  OmniPanel,
  OmniSkeleton,
  OmniStatusDot,
  OmniTabs,
  OmniTextarea,
  OmniTooltip,
} from '.'

describe('Omni design system primitives', () => {
  it('renders button variants and preserves disabled behavior', async () => {
    const onClick = vi.fn()
    render(
      <OmniButton disabled onClick={onClick} variant="danger">
        Remover
      </OmniButton>,
    )

    const button = screen.getByRole('button', { name: 'Remover' })
    expect(button).toBeDisabled()
    expect(button.className).toContain('bg-red-500/20')
    await userEvent.click(button)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('renders card, panel, badge, status, and skeleton states safely', () => {
    const { container } = render(
      <>
        <OmniCard data-testid="card">Card</OmniCard>
        <OmniPanel data-testid="panel">Panel</OmniPanel>
        <OmniBadge tone="warning">Atenção</OmniBadge>
        <OmniStatusDot label="Operacional" tone="success" />
        <OmniSkeleton lines={0} />
      </>,
    )

    expect(screen.getByTestId('card')).toHaveClass('omni-card')
    expect(screen.getByTestId('panel')).toHaveTextContent('Panel')
    expect(screen.getByText('Atenção')).toHaveAttribute('data-tone', 'warning')
    expect(screen.getByRole('status', { name: 'Operacional' })).toHaveAttribute('data-tone', 'success')
    expect(container.querySelectorAll('.omni-skeleton')).toHaveLength(1)
  })

  it('forwards safe input and textarea attributes and disabled states', () => {
    render(
      <>
        <OmniInput aria-label="Nome" disabled placeholder="Nome" />
        <OmniTextarea aria-label="Descrição" rows={4} />
      </>,
    )

    expect(screen.getByRole('textbox', { name: 'Nome' })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: 'Descrição' })).toHaveAttribute('rows', '4')
  })

  it('supports tab selection and keyboard navigation basics', () => {
    function TabsHarness() {
      const [activeTab, setActiveTab] = useState('summary')
      return (
        <>
          <OmniTabs
            activeTab={activeTab}
            onSelect={setActiveTab}
            tabs={[
              { id: 'summary', label: 'Summary' },
              { id: 'provider', label: 'Provider' },
              { id: 'logs', label: 'Logs' },
            ]}
          />
          <div id={`tabpanel-${activeTab}`} role="tabpanel">
            {activeTab}
          </div>
        </>
      )
    }

    render(<TabsHarness />)
    const summary = screen.getByRole('tab', { name: 'Summary' })
    fireEvent.keyDown(summary, { key: 'End' })

    const logs = screen.getByRole('tab', { name: 'Logs' })
    expect(logs).toHaveAttribute('aria-selected', 'true')
    expect(logs).toHaveFocus()
    expect(screen.getByRole('tabpanel')).toHaveTextContent('logs')
  })

  it('shows tooltip content on keyboard focus without unsafe HTML rendering', () => {
    render(
      <OmniTooltip content={'<script>alert("unsafe")</script>'}>
        <button type="button">Ajuda</button>
      </OmniTooltip>,
    )

    fireEvent.focus(screen.getByRole('button', { name: 'Ajuda' }))
    expect(screen.getByRole('tooltip')).toHaveTextContent('<script>alert("unsafe")</script>')
    expect(document.querySelector('script')).not.toBeInTheDocument()
  })
})

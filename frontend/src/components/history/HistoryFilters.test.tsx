import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { HistoryFilters } from './HistoryFilters'

describe('HistoryFilters design system adoption', () => {
  it('preserves mode selection and sort behavior', () => {
    const onModeFilter = vi.fn()
    const onSortChange = vi.fn()

    render(
      <HistoryFilters
        onModeFilter={onModeFilter}
        onSearchChange={vi.fn()}
        onSortChange={onSortChange}
      />,
    )

    const codeButton = screen.getByRole('button', { name: 'Código' })
    fireEvent.click(codeButton)
    expect(onModeFilter).toHaveBeenCalledWith('codigo')
    expect(codeButton).toHaveClass('bg-neon-purple/15')

    const sortButton = screen.getByRole('button', { name: '↓ Recentes' })
    fireEvent.click(sortButton)
    expect(onSortChange).toHaveBeenCalledWith('oldest')
    expect(screen.getByRole('button', { name: '↑ Antigas' })).toBeInTheDocument()
  })

  it('keeps the search input on the Omni control primitive', () => {
    render(
      <HistoryFilters
        onModeFilter={vi.fn()}
        onSearchChange={vi.fn()}
        onSortChange={vi.fn()}
      />,
    )

    expect(screen.getByPlaceholderText('Buscar sessões...')).toHaveClass('omni-control')
  })
})

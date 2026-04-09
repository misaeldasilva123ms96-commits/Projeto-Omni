import type { ChatMode } from '../types'

const MODES: Array<{ description: string; id: ChatMode; label: string }> = [
  { id: 'chat', label: 'Chat', description: 'General runtime conversation' },
  { id: 'pesquisa', label: 'Pesquisa', description: 'Research and synthesis' },
  { id: 'codigo', label: 'Codigo', description: 'Code-focused assistance' },
  { id: 'agente', label: 'Agente', description: 'Agentic execution posture' },
]

type ModeSwitcherProps = {
  mode: ChatMode
  onChangeMode: (mode: ChatMode) => void
}

export function ModeSwitcher({ mode, onChangeMode }: ModeSwitcherProps) {
  return (
    <div className="mode-switcher">
      <p className="sidebar-label">Modo</p>
      <div className="mode-grid">
        {MODES.map((item) => (
          <button
            key={item.id}
            className={item.id === mode ? 'mode-chip active' : 'mode-chip'}
            onClick={() => onChangeMode(item.id)}
            type="button"
          >
            <span>{item.label}</span>
            <small>{item.description}</small>
          </button>
        ))}
      </div>
    </div>
  )
}

import { motion } from 'framer-motion'
import type { ChatRequestState, RuntimeMetadata } from '../../types'
import type { UiRuntimeStatus } from '../../types/ui/runtime'
import { TOP_ACTIONS, useRuntimeConsoleStore } from '../../state/runtimeConsoleStore'
import { useLiveRuntimeMetrics } from '../../hooks/useLiveRuntimeMetrics'
import { getGlowState } from '../../lib/ui/glow'
import { RuntimeInspectorPanel } from '../runtime/RuntimeInspectorPanel'

type RuntimePanelProps = {
  health: UiRuntimeStatus | null
  lastMetadata: RuntimeMetadata | null
  modeLabel: string
  requestState: ChatRequestState
  sessionId: string
}

export function RuntimePanel({ health, lastMetadata, modeLabel, requestState, sessionId }: RuntimePanelProps) {
  const activeAction = useRuntimeConsoleStore((state) => state.activeAction)
  const selectTopAction = useRuntimeConsoleStore((state) => state.selectTopAction)
  const setUiNotice = useRuntimeConsoleStore((state) => state.setUiNotice)
  const runtimeActive = requestState === 'loading' || lastMetadata?.signals?.node_execution_successful === true

  return (
    <motion.div
      className={`flex h-full flex-col overflow-hidden rounded-[26px] border bg-[linear-gradient(180deg,rgba(14,16,36,0.9),rgba(11,13,29,0.84))] px-3.5 py-4 shadow-[0_20px_52px_rgba(0,0,0,0.36)] backdrop-blur-xl ${runtimeActive ? `${getGlowState('runtime')} omni-runtime-glow` : 'border-[rgba(98,141,255,0.16)]'}`}
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      <div className="mb-3 border-b border-white/10 pb-3">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[radial-gradient(circle_at_40%_35%,rgba(255,255,255,0.92),rgba(181,109,255,0.76)_28%,rgba(78,164,255,0.72)_58%,rgba(9,12,28,0.45)_72%)] shadow-[0_0_24px_rgba(123,97,255,0.38)]" />
            <div>
              <div className="text-[20px] font-semibold tracking-tight text-white">Omni AI</div>
              <div className="text-xs text-slate-300/70">Runtime Intelligence</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-teal-300 omni-active-dot" />
            <button
              className={`rounded-full border border-white/10 bg-white/[0.05] p-2 text-slate-200/80 transition hover:text-white active:translate-y-px ${getGlowState('hover')}`}
              onClick={() => setUiNotice('Runtime Intelligence está em modo monitor. Use Logs para abrir detalhes de observabilidade.')}
              type="button"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" /></svg>
            </button>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-sm">
          {TOP_ACTIONS.slice(0, 3).map((item) => {
            const active = activeAction === item.id
            return (
              <button
                key={item.id}
                className={`rounded-2xl border px-2.5 py-1.5 text-slate-200/85 transition ${active ? `bg-white/[0.07] ${getGlowState('active')}` : `border-white/8 bg-white/[0.04] ${getGlowState('hover')}`}`}
                onClick={() => selectTopAction(item.id)}
                type="button"
              >
                {item.label}
              </button>
            )
          })}
        </div>
      </div>

      <RuntimeInspectorPanel
        metadata={lastMetadata}
        sessionId={sessionId}
        requestState={requestState}
      />
    </motion.div>
  )
}

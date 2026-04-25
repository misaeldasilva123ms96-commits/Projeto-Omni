import { motion } from 'framer-motion'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ChatRequestState, RuntimeMetadata } from '../../types'
import type { UiRuntimeStatus } from '../../types/ui/runtime'
import { TOP_ACTIONS, mockRuntimeState, useRuntimeConsoleStore } from '../../state/runtimeConsoleStore'
import { useLiveRuntimeMetrics } from '../../hooks/useLiveRuntimeMetrics'
import { getGlowState } from '../../lib/ui/glow'

type RuntimePanelProps = {
  health: UiRuntimeStatus | null
  lastMetadata: RuntimeMetadata | null
  modeLabel: string
  requestState: ChatRequestState
  sessionId: string
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null
}

function nestedNumber(value: unknown, keys: string[]): number | null {
  let cursor: unknown = value
  for (const key of keys) {
    const record = asRecord(cursor)
    if (!record) {
      return null
    }
    cursor = record[key]
  }
  return typeof cursor === 'number' ? cursor : null
}

function nestedString(value: unknown, keys: string[]): string | null {
  let cursor: unknown = value
  for (const key of keys) {
    const record = asRecord(cursor)
    if (!record) {
      return null
    }
    cursor = record[key]
  }
  return typeof cursor === 'string' && cursor.trim() ? cursor.trim() : null
}

function inferConfidence(metadata: RuntimeMetadata | null) {
  return (
    nestedNumber(metadata?.cognitiveRuntimeInspection, ['signals', 'decision_confidence'])
    ?? nestedNumber(metadata?.cognitiveRuntimeInspection, ['confidence'])
    ?? mockRuntimeState.confidence
  )
}

function inferStrategy(metadata: RuntimeMetadata | null) {
  return (
    nestedString(metadata?.cognitiveRuntimeInspection, ['strategy'])
    ?? metadata?.runtimeReason
    ?? metadata?.executionPathUsed
    ?? mockRuntimeState.strategy
  )
}

function inferExecutionTime(metadata: RuntimeMetadata | null) {
  const numeric =
    nestedNumber(metadata?.cognitiveRuntimeInspection, ['signals', 'execution_time_ms'])
    ?? nestedNumber(metadata?.executionProvenance, ['latency_ms'])
  if (typeof numeric === 'number') {
    return `${(numeric / 1000).toFixed(2)}s`
  }
  return mockRuntimeState.executionTime
}

function inferMemoryStatus(metadata: RuntimeMetadata | null) {
  if (metadata?.cognitiveRuntimeInspection) {
    return nestedString(metadata.cognitiveRuntimeInspection, ['memory_status']) ?? mockRuntimeState.memoryStatus
  }
  return mockRuntimeState.memoryStatus
}

function simulationPaths(metadata: RuntimeMetadata | null) {
  if (metadata?.matchedTools?.length) {
    return metadata.matchedTools.map((tool, index) => `${index + 1}. Decisão avaliada com ${tool}`)
  }
  if (metadata?.matchedCommands?.length) {
    return metadata.matchedCommands.map((command, index) => `${index + 1}. Sinal operacional: ${command}`)
  }
  return mockRuntimeState.rankedDecisions.map((item, index) => `${index + 1}. ${item}`)
}

function goalProgress(metadata: RuntimeMetadata | null) {
  if (metadata?.fallbackTriggered) {
    return 0.24
  }
  if (metadata?.toolExecution?.tool_succeeded) {
    return 0.82
  }
  if (metadata?.executionPathUsed) {
    return 0.56
  }
  return mockRuntimeState.goalProgress
}

function RuntimeMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/8 py-2.5 last:border-b-0">
      <span className="text-sm text-slate-300/70">{label}</span>
      <span className="text-right text-sm font-medium text-white">{value}</span>
    </div>
  )
}

export function RuntimePanel({ health, lastMetadata, modeLabel, requestState, sessionId }: RuntimePanelProps) {
  const activeAction = useRuntimeConsoleStore((state) => state.activeAction)
  const selectTopAction = useRuntimeConsoleStore((state) => state.selectTopAction)
  const setUiNotice = useRuntimeConsoleStore((state) => state.setUiNotice)
  const runtimeActive = requestState === 'loading' || lastMetadata?.signals?.node_execution_successful === true
  const liveMetrics = useLiveRuntimeMetrics(runtimeActive)
  const confidence = lastMetadata ? inferConfidence(lastMetadata) : liveMetrics.confidence
  const progress = lastMetadata ? goalProgress(lastMetadata) : liveMetrics.progress
  const ranked = simulationPaths(lastMetadata)
  const runtimeMode = lastMetadata?.runtimeMode ?? health?.runtimeMode ?? modeLabel ?? 'Cognitive Runtime'
  const executionTime = lastMetadata ? inferExecutionTime(lastMetadata) : liveMetrics.executionTime

  return (
    <motion.div
      className={`flex h-full flex-col overflow-hidden rounded-[28px] border bg-[linear-gradient(180deg,rgba(14,16,36,0.9),rgba(11,13,29,0.84))] px-4 py-5 shadow-[0_20px_52px_rgba(0,0,0,0.36)] backdrop-blur-xl ${runtimeActive ? `${getGlowState('runtime')} omni-runtime-glow` : 'border-[rgba(98,141,255,0.16)]'}`}
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      <div className="mb-4 border-b border-white/10 pb-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[radial-gradient(circle_at_40%_35%,rgba(255,255,255,0.92),rgba(181,109,255,0.76)_28%,rgba(78,164,255,0.72)_58%,rgba(9,12,28,0.45)_72%)] shadow-[0_0_24px_rgba(123,97,255,0.38)]" />
            <div>
              <div className="text-[22px] font-semibold tracking-tight text-white">Omni AI</div>
              <div className="text-sm text-slate-300/70">Runtime Intelligence</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-teal-300 omni-active-dot" />
            <button className={`rounded-full border border-white/10 bg-white/[0.05] p-2 text-slate-200/80 transition hover:text-white active:translate-y-px ${getGlowState('hover')}`} onClick={() => setUiNotice('Runtime Intelligence está em modo monitor. Use Logs para abrir detalhes de observabilidade.')} type="button">
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
                className={`rounded-2xl border px-3 py-2 text-slate-200/85 transition ${active ? `bg-white/[0.07] ${getGlowState('active')}` : `border-white/8 bg-white/[0.04] ${getGlowState('hover')}`}`}
                onClick={() => selectTopAction(item.id)}
                type="button"
              >
                {item.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        <section className="rounded-[24px] border border-white/10 bg-black/15 px-4 py-4">
          <h3 className="mb-3 text-[18px] font-medium tracking-tight text-white">Runtime Status</h3>
          <RuntimeMetric label="Mode" value={runtimeMode} />
          <RuntimeMetric label="Strategy" value={inferStrategy(lastMetadata)} />
          <div className="border-b border-white/8 py-2.5">
            <div className="mb-2 flex items-center justify-between gap-4">
              <span className="text-sm text-slate-300/70">Confidence</span>
              <span className="text-right text-sm font-medium text-white">{confidence.toFixed(2)}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <motion.div
                animate={{ width: `${Math.round(confidence * 100)}%` }}
                className="h-full rounded-full bg-[linear-gradient(90deg,rgba(181,109,255,0.9),rgba(81,246,255,0.85))]"
                transition={{ duration: 0.45, ease: 'easeOut' }}
              />
            </div>
          </div>
          <RuntimeMetric label="Execution Time" value={executionTime} />
          <RuntimeMetric label="Memory" value={inferMemoryStatus(lastMetadata)} />
        </section>

        <section className="rounded-[24px] border border-white/10 bg-black/15 px-4 py-4">
          <h3 className="mb-3 text-[18px] font-medium tracking-tight text-white">Goal Model</h3>
          <div className="space-y-3">
            <div>
              <div className="text-sm text-slate-300/70">Current Goal</div>
              <div className="mt-1 text-base text-white">
                {lastMetadata?.matchedCommands?.[0] ?? mockRuntimeState.currentGoal}
              </div>
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between text-sm text-slate-300/70">
                <span>Progress</span>
                <span>{Math.round(progress * 100)}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-white/10">
                <motion.div
                  className="h-full rounded-full bg-[linear-gradient(90deg,rgba(181,109,255,0.85),rgba(78,164,255,0.95))]"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.max(progress, 0.08) * 100}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                />
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-[24px] border border-white/10 bg-black/15 px-4 py-4">
          <h3 className="mb-3 text-[18px] font-medium tracking-tight text-white">Simulation</h3>
          <div className="mb-3 text-sm text-slate-300/70">
            Paths considered: {lastMetadata?.matchedTools?.length ?? mockRuntimeState.pathsConsidered}
          </div>
          <ol className="space-y-2 text-sm leading-6 text-slate-100/90">
            {ranked.slice(0, 3).map((item) => (
              <li key={item} className="rounded-2xl border border-white/8 bg-white/[0.03] px-3 py-3">
                {item}
              </li>
            ))}
          </ol>
        </section>

        <section className="rounded-[24px] border border-white/10 bg-black/15 px-4 py-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h3 className="text-[18px] font-medium tracking-tight text-white">Cognitive Evolution</h3>
              <div className="mt-1 text-sm text-slate-300/70">Run ID: {sessionId || mockRuntimeState.runId}</div>
            </div>
            <div className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-xs uppercase tracking-[0.28em] text-slate-300">
              live
            </div>
          </div>
          <div className="h-48 rounded-[22px] border border-white/8 bg-[rgba(7,10,24,0.86)] p-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={liveMetrics.graph}>
                <XAxis axisLine={false} dataKey="label" tick={{ fill: '#9fb0d7', fontSize: 11 }} tickLine={false} />
                <YAxis axisLine={false} domain={[0, 1]} tick={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(11, 15, 34, 0.92)',
                    border: '1px solid rgba(181,109,255,0.25)',
                    borderRadius: '16px',
                    color: '#fff',
                  }}
                />
                <Line dataKey="confidence" dot={{ r: 3 }} stroke="#4ea4ff" strokeWidth={2.5} type="monotone" />
                <Line dataKey="execution" dot={{ r: 3 }} stroke="#b56dff" strokeWidth={2.2} type="monotone" />
                <Line dataKey="memory" dot={{ r: 3 }} stroke="#51f6ff" strokeWidth={2} type="monotone" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </motion.div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { mockRuntimeState, type RuntimeGraphPoint } from '../state/runtimeConsoleStore'

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

export function useLiveRuntimeMetrics(runtimeActive: boolean) {
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const id = window.setInterval(() => {
      setTick((value) => value + 1)
    }, runtimeActive ? 900 : 1600)

    return () => window.clearInterval(id)
  }, [runtimeActive])

  return useMemo(() => {
    const wave = Math.sin(tick / 2.2)
    const confidence = clamp(mockRuntimeState.confidence + wave * 0.035, 0.72, 0.96)
    const progress = clamp(mockRuntimeState.goalProgress + (runtimeActive ? 0.08 : 0) + Math.cos(tick / 2.8) * 0.018, 0.18, 0.92)
    const executionSeconds = clamp(1.12 + Math.abs(Math.sin(tick / 1.8)) * 0.38, 0.72, 1.86)
    const graph: RuntimeGraphPoint[] = mockRuntimeState.evolution.map((point, index) => ({
      ...point,
      confidence: clamp(point.confidence + Math.sin((tick + index) / 3) * 0.025, 0, 1),
      execution: clamp(point.execution + Math.cos((tick + index) / 2.7) * 0.025, 0, 1),
      memory: clamp(point.memory + Math.sin((tick + index) / 2.4) * 0.018, 0, 1),
    }))

    return {
      confidence,
      executionTime: `${executionSeconds.toFixed(2)}s`,
      graph,
      progress,
      tick,
    }
  }, [runtimeActive, tick])
}

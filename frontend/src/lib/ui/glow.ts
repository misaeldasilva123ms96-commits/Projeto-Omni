export type GlowState = 'hover' | 'active' | 'focus' | 'runtime'

const glowStateClasses: Record<GlowState, string> = {
  hover: 'hover:border-neon-blue/35 hover:shadow-[0_0_0_1px_rgba(78,164,255,0.12),0_0_16px_rgba(78,164,255,0.14)]',
  active: 'border-neon-purple/60 shadow-[0_0_0_1px_rgba(181,109,255,0.18),0_0_22px_rgba(181,109,255,0.22)]',
  focus: 'focus-within:border-neon-cyan/55 focus-within:shadow-[0_0_0_1px_rgba(81,246,255,0.18),0_0_22px_rgba(81,246,255,0.16)]',
  runtime: 'border-neon-cyan/40 shadow-[0_0_0_1px_rgba(81,246,255,0.14),0_0_18px_rgba(81,246,255,0.18)]',
}

export function getGlowState(type: GlowState) {
  return glowStateClasses[type]
}

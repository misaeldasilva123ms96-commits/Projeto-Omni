import { motion } from 'framer-motion'
import { useCallback } from 'react'
import { MarkdownRenderer } from '../MarkdownRenderer'
import type { ChatMessage, RuntimeMetadata } from '../../types'

type OmniAssistantMessageProps = {
  message: ChatMessage & { isLoading?: boolean }
  onCopy?: (content: string) => void
  onRetry?: () => void
  getBadges?: (metadata?: RuntimeMetadata) => string[]
  className?: string
}

export function OmniAssistantMessage({ message, onCopy, onRetry, getBadges, className = '' }: OmniAssistantMessageProps) {
  const badges = getBadges?.(message.metadata) ?? []
  const hasActions = !!onCopy || !!onRetry

  const handleCopy = useCallback(() => {
    onCopy?.(message.content)
  }, [message.content, onCopy])

  const handleRetry = useCallback(() => {
    onRetry?.()
  }, [onRetry])

  return (
    <motion.article
      className={`w-full max-w-[84%] rounded-[28px] border bg-[linear-gradient(180deg,rgba(15,15,32,0.88),rgba(8,9,22,0.74))] px-8 py-6 text-slate-100 shadow-[0_14px_34px_rgba(0,0,0,0.28)] backdrop-blur-xl ${message.isLoading ? 'border-neon-cyan/40' : 'border-[rgba(180,109,255,0.16)]'} ${className}`.trim()}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28 }}
    >
      <div className="mb-4 flex items-center justify-between gap-4 text-xs uppercase tracking-[0.32em] text-slate-300/70">
        <span>Omni Runtime</span>
        <span>{new Date(message.createdAt).toLocaleTimeString('pt-BR')}</span>
      </div>

      {message.isLoading ? (
        <div className="space-y-4 py-3">
          <div className="flex items-center gap-2">
            {[0, 1, 2].map((dot) => (
              <span
                key={dot}
                className="h-2.5 w-2.5 animate-shimmer rounded-full bg-gradient-to-r from-neon-purple via-neon-blue to-neon-cyan"
                style={{ animationDelay: `${dot * 140}ms` }}
              />
            ))}
          </div>
          <div className="space-y-2">
            <div className="h-3 w-5/6 rounded-full bg-white/10 omni-skeleton" />
            <div className="h-3 w-3/4 rounded-full bg-white/10 omni-skeleton" />
            <div className="h-3 w-2/3 rounded-full bg-white/10 omni-skeleton" />
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <MarkdownRenderer content={message.content || '...'} />
          {badges.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {badges.map((badge) => (
                <span
                  key={badge}
                  className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-200/75"
                >
                  {badge}
                </span>
              ))}
            </div>
          ) : null}
          {hasActions ? (
            <div className="flex justify-end gap-3 text-violet-200/80">
              {onCopy ? (
                <button
                  className="rounded-full border border-white/8 bg-white/[0.04] p-2 transition hover:border-neon-cyan/40 hover:text-white"
                  onClick={handleCopy}
                  type="button"
                  title="Copy response"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M5 15H3V3h12v2M9 9h12v12H9V9Z" /></svg>
                </button>
              ) : null}
              {onRetry ? (
                <button
                  className="rounded-full border border-white/8 bg-white/[0.04] p-2 transition hover:border-neon-blue/40 hover:text-white"
                  onClick={handleRetry}
                  type="button"
                  title="Retry"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M21 12a9 9 0 0 0-9-9M3 12a9 9 0 0 0 9 9M3 3l3 9-3 9" /></svg>
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      )}
    </motion.article>
  )
}

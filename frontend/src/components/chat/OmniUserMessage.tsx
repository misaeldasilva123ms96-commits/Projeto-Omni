import type { ChatMessage } from '../../types'

type OmniUserMessageProps = {
  message: ChatMessage
  className?: string
}

export function OmniUserMessage({ message, className = '' }: OmniUserMessageProps) {
  return (
    <div className={`flex justify-end ${className}`.trim()}>
      <div className="max-w-[72%] rounded-[26px] border border-blue-500/30 bg-[linear-gradient(135deg,rgba(28,60,190,0.74),rgba(10,24,74,0.98))] px-8 py-4 text-right text-[18px] font-medium leading-8 tracking-tight text-white shadow-[0_0_20px_rgba(59,130,246,0.18)]">
        {message.content || '...'}
      </div>
    </div>
  )
}

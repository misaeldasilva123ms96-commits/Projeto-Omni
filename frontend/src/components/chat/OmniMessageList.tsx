import { useRef, useEffect, type ReactNode } from 'react'

type OmniMessageListProps = {
  children: ReactNode
  className?: string
  emptyState?: ReactNode
  hasMessages?: boolean
}

export function OmniMessageList({ children, className = '', emptyState, hasMessages = false }: OmniMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [children])

  if (!hasMessages && emptyState) {
    return <div className="flex flex-1 items-center justify-center">{emptyState}</div>
  }

  return (
    <div className={`flex max-h-[calc(100vh-18rem)] min-h-[360px] flex-col gap-4 overflow-y-auto pr-2 ${className}`.trim()}>
      {children}
      <div ref={bottomRef} />
    </div>
  )
}

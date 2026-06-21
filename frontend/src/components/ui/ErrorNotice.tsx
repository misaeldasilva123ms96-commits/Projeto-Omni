import { OmniErrorState } from './OmniErrorState'

export type ErrorNoticeProps = {
  message: string
  title?: string
  className?: string
}

export function ErrorNotice({ message, title, className = '' }: ErrorNoticeProps) {
  return <OmniErrorState className={className} description={message} size="compact" title={title} />
}

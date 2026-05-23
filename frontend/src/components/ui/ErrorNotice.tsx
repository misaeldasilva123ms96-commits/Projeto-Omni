export type ErrorNoticeProps = {
  message: string
  title?: string
  className?: string
}

export function ErrorNotice({ message, title, className = '' }: ErrorNoticeProps) {
  return (
    <div className={`omni-error-notice ${className}`.trim()} role="alert">
      {title ? <p className="sidebar-label">{title}</p> : null}
      <p className="error-text">{message}</p>
    </div>
  )
}

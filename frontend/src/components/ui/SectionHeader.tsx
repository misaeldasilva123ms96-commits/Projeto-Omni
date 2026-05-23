import type { ReactNode } from 'react'

type TitleLevel = 'h1' | 'h2' | 'h3'

export type SectionHeaderProps = {
  eyebrow?: string
  eyebrowClassName?: string
  title: string
  subtitle?: string
  titleElement?: TitleLevel
  /** Extra actions or meta aligned with the title block */
  aside?: ReactNode
  className?: string
}

export function SectionHeader({
  eyebrow,
  eyebrowClassName = 'eyebrow',
  title,
  subtitle,
  titleElement = 'h2',
  aside,
  className = '',
}: SectionHeaderProps) {
  const TitleTag = titleElement
  return (
    <header className={`omni-section-header ${className}`.trim()}>
      <div className="omni-section-header__main">
        {eyebrow ? <p className={eyebrowClassName}>{eyebrow}</p> : null}
        <TitleTag>{title}</TitleTag>
        {subtitle ? <p className="subtitle">{subtitle}</p> : null}
      </div>
      {aside ? <div className="omni-section-header__aside">{aside}</div> : null}
    </header>
  )
}

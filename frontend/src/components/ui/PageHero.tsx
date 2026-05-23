import type { ReactNode } from 'react'
import { PanelCard } from './PanelCard'
import { SectionHeader } from './SectionHeader'

export type PageHeroProps = {
  eyebrow: string
  title: string
  subtitle?: string
  /** Status pills, errors, or connection labels */
  meta?: ReactNode
  className?: string
}

/** Hero band for dashboard / observability primary context. */
export function PageHero({ eyebrow, title, subtitle, meta, className = '' }: PageHeroProps) {
  return (
    <PanelCard className={`hero-card dashboard-hero omni-page-hero ${className}`.trim()}>
      <div>
        <SectionHeader eyebrow={eyebrow} title={title} subtitle={subtitle} />
      </div>
      {meta ? <div className="hero-meta">{meta}</div> : null}
    </PanelCard>
  )
}

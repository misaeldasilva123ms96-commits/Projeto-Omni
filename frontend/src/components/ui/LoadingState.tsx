import { OmniLoadingState, type OmniLoadingStateProps } from './OmniLoadingState'

export type LoadingStateProps = Pick<OmniLoadingStateProps, 'label' | 'className'>

export function LoadingState({ label = 'Carregando…', className = '' }: LoadingStateProps) {
  return <OmniLoadingState className={className} label={label} size="compact" />
}

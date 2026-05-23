import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ActionButtonVariant = 'primary' | 'ghost'

export type ActionButtonProps = {
  children: ReactNode
  variant?: ActionButtonVariant
} & ButtonHTMLAttributes<HTMLButtonElement>

export function ActionButton({
  children,
  variant = 'ghost',
  className = '',
  type = 'button',
  ...rest
}: ActionButtonProps) {
  const base = variant === 'primary' ? 'send-button' : 'ghost-button'
  return (
    <button className={`${base} ${className}`.trim()} type={type} {...rest}>
      {children}
    </button>
  )
}

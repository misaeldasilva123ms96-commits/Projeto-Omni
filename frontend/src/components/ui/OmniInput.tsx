import type { InputHTMLAttributes } from 'react'

export type OmniInputProps = InputHTMLAttributes<HTMLInputElement>

export function OmniInput({ className = '', type = 'text', ...rest }: OmniInputProps) {
  return (
    <input
      className={`omni-control w-full rounded-2xl border px-4 py-2.5 text-sm outline-none transition disabled:cursor-not-allowed disabled:opacity-60 ${className}`.trim()}
      type={type}
      {...rest}
    />
  )
}

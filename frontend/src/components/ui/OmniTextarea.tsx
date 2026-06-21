import type { TextareaHTMLAttributes } from 'react'

export type OmniTextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>

export function OmniTextarea({ className = '', ...rest }: OmniTextareaProps) {
  return (
    <textarea
      className={`omni-control w-full rounded-2xl border px-4 py-2.5 text-sm outline-none transition disabled:cursor-not-allowed disabled:opacity-60 ${className}`.trim()}
      {...rest}
    />
  )
}

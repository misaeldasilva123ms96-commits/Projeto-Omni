import { useEffect, useRef, useState } from 'react'

export interface UseTypewriterOptions {
  speed?: number
  onComplete?: () => void
}

export function useTypewriter(
  text: string,
  options?: UseTypewriterOptions,
): { displayed: string; isTyping: boolean } {
  const speed = options?.speed ?? 18
  const intervalRef = useRef<number | null>(null)
  const onCompleteRef = useRef(options?.onComplete)
  const [displayed, setDisplayed] = useState('')
  const [isTyping, setIsTyping] = useState(false)

  useEffect(() => {
    onCompleteRef.current = options?.onComplete
  }, [options?.onComplete])

  useEffect(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    if (!text) {
      setDisplayed('')
      setIsTyping(false)
      return
    }

    let index = 0
    setDisplayed('')
    setIsTyping(true)

    intervalRef.current = window.setInterval(() => {
      index += 1
      setDisplayed(text.slice(0, index))

      if (index >= text.length) {
        if (intervalRef.current !== null) {
          window.clearInterval(intervalRef.current)
          intervalRef.current = null
        }
        setIsTyping(false)
        onCompleteRef.current?.()
      }
    }, speed)

    return () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [speed, text])

  return { displayed, isTyping }
}

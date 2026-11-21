import { useEffect, useState } from 'react'

/** Animates a number from 0 up to `target`. */
export function useCountUp(target: number, durationMs = 1200): number {
  const [value, setValue] = useState(0)

  useEffect(() => {
    let frame = 0
    const startTime = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - startTime) / durationMs)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(Math.round(eased * target))
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, durationMs])

  return value
}

/** Seconds elapsed since `startedAt`, ticking while `running`. */
export function useElapsed(startedAt: number | null, finishedAt: number | null): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (startedAt === null || finishedAt !== null) return
    const id = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(id)
  }, [startedAt, finishedAt])

  if (startedAt === null) return 0
  return Math.max(0, Math.floor(((finishedAt ?? now) - startedAt) / 1000))
}

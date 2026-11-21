import { flushSync } from 'react-dom'

/**
 * Run a state update inside a View Transition when the browser supports it,
 * so elements with the same `view-transition-name` (the logo, the pipeline)
 * morph smoothly between the home and dashboard layouts.
 */
export function withViewTransition(update: () => void): void {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (!document.startViewTransition || reduceMotion) {
    update()
    return
  }
  document.startViewTransition(() => {
    flushSync(update)
  })
}

/** Decorative animated backdrop: a moving perspective grid, glowing orbs and scanlines. */
export function Background() {
  return (
    <div className="bg" aria-hidden="true">
      <div className="bg-orb bg-orb--cyan" />
      <div className="bg-orb bg-orb--magenta" />
      <div className="bg-orb bg-orb--violet" />
      <div className="bg-grid" />
      <div className="bg-scanlines" />
    </div>
  )
}

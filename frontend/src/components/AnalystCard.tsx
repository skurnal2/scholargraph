import { useState } from 'react'
import type { PaperSectionHit } from '../lib/types'
import { AgentIcon } from './Icons'

interface Props {
  sections: PaperSectionHit[] | null
  claimCount: number
  onInspect?: () => void
}

/** First card in the live feed: what the Paper Analyst read and what it found, before any code is checked. */
export function AnalystCard({ sections, claimCount, onInspect }: Props) {
  const [open, setOpen] = useState(false)
  const shown = sections ?? []

  return (
    <li className="analyst-card">
      <div className="analyst-head">
        <span className="analyst-icon">
          <AgentIcon agent="analyst" />
        </span>
        <div className="analyst-summary">
          <span className="analyst-title">Paper Analyst</span>
          <span className="analyst-line">
            {sections ? (
              <>
                read <strong>{shown.length}</strong> section{shown.length === 1 ? '' : 's'} via hybrid search →{' '}
              </>
            ) : null}
            extracted <strong>{claimCount}</strong> claim{claimCount === 1 ? '' : 's'}
          </span>
        </div>
        {onInspect && (
          <button className="ghost ghost--small" onClick={onInspect}>
            Details
          </button>
        )}
      </div>

      {shown.length > 0 && (
        <>
          <div className="chips analyst-chips">
            {shown.slice(0, open ? shown.length : 6).map((s, i) => (
              <span className="chip chip--section" key={`${s.section}-${i}`} title={s.topics.join(' · ')}>
                {s.section}
                <span className="chip-score">{s.score.toFixed(2)}</span>
              </span>
            ))}
            {shown.length > 6 && (
              <button className="chip chip--more" onClick={() => setOpen((o) => !o)}>
                {open ? 'show less' : `+${shown.length - 6} more`}
              </button>
            )}
          </div>
        </>
      )}
    </li>
  )
}

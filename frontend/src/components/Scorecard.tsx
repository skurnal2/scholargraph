import { useState } from 'react'
import { useCountUp } from '../lib/hooks'
import type { ResultRow, VerdictStatus } from '../lib/types'
import { ChevronIcon } from './Icons'
import { StatusBadge } from './Timeline'

function Tile({ label, value, tone, delay }: { label: string; value: number; tone: string; delay: number }) {
  const shown = useCountUp(value)
  return (
    <div className={`tile tile--${tone}`} style={{ animationDelay: `${delay}ms` }}>
      <span className="tile-value">{shown}</span>
      <span className="tile-label">{label}</span>
    </div>
  )
}

function ScoreRing({ percent }: { percent: number }) {
  const shown = useCountUp(percent, 1600)
  const radius = 52
  const circumference = 2 * Math.PI * radius
  return (
    <div className="ring">
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <defs>
          <linearGradient id="ring-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--neon-cyan)" />
            <stop offset="100%" stopColor="var(--neon-magenta)" />
          </linearGradient>
        </defs>
        <circle className="ring-track" cx="60" cy="60" r={radius} />
        <circle
          className="ring-value"
          cx="60"
          cy="60"
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - shown / 100)}
        />
      </svg>
      <div className="ring-text">
        <span className="ring-number">{shown}%</span>
        <span className="ring-caption">agreement</span>
      </div>
    </div>
  )
}

function headline(counts: Record<VerdictStatus, number>): { title: string; tone: string } {
  if (counts.MISMATCH === 0 && counts.NOT_FOUND === 0) return { title: 'Full match', tone: 'match' }
  if (counts.MISMATCH > 0) {
    const n = counts.MISMATCH
    return { title: `Partial match · ${n} mismatch${n === 1 ? '' : 'es'}`, tone: 'mismatch' }
  }
  return { title: `Unverified · ${counts.NOT_FOUND} not found`, tone: 'not_found' }
}

function ResultItem({ row, index }: { row: ResultRow; index: number }) {
  const [open, setOpen] = useState(row.status !== 'MATCH')
  const files = row.where.split(',').map((s) => s.trim()).filter(Boolean)
  return (
    <li className={`result result--${row.status.toLowerCase()}`} style={{ animationDelay: `${300 + index * 70}ms` }}>
      <button className="result-head" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <StatusBadge status={row.status} />
        <span className="result-claim">{row.claim}</span>
        <ChevronIcon open={open} />
      </button>
      {open && (
        <div className="result-body">
          <div className="compare">
            <div className="compare-side">
              <span className="compare-label">Paper says</span>
              <span className="compare-value">{row.paper}</span>
            </div>
            <span className="compare-vs">vs</span>
            <div className="compare-side">
              <span className="compare-label">Code does</span>
              <code className="compare-value compare-value--code">{row.code}</code>
            </div>
          </div>
          <blockquote className="quote">
            “{row.quote}”
            <cite>Section {row.section}</cite>
          </blockquote>
          <div className="chips">
            <span className="chips-label">Evidence</span>
            {files.map((file) => (
              <code className="chip" key={file}>{file}</code>
            ))}
          </div>
        </div>
      )}
    </li>
  )
}

/** Final report: animated counters, agreement ring and the claim-by-claim breakdown. */
export function Scorecard({ results, seconds }: { results: ResultRow[]; seconds: number }) {
  const [onlyIssues, setOnlyIssues] = useState(false)
  const counts: Record<VerdictStatus, number> = { MATCH: 0, MISMATCH: 0, NOT_FOUND: 0 }
  for (const r of results) counts[r.status] += 1
  const percent = results.length ? Math.round((counts.MATCH / results.length) * 100) : 0
  const summary = headline(counts)
  const rows = onlyIssues ? results.filter((r) => r.status !== 'MATCH') : results

  return (
    <section className="panel scorecard" aria-label="Verification scorecard">
      <header className="panel-head">
        <h2 className="panel-title">Scorecard</h2>
        <span className="panel-meta">completed in {seconds}s</span>
      </header>

      <div className="score-top">
        <ScoreRing percent={percent} />
        <div className="score-summary">
          <p className={`verdict verdict--${summary.tone}`}>{summary.title}</p>
          <div className="tiles">
            <Tile label="claims" value={results.length} tone="total" delay={0} />
            <Tile label="match" value={counts.MATCH} tone="match" delay={90} />
            <Tile label="mismatch" value={counts.MISMATCH} tone="mismatch" delay={180} />
            <Tile label="not found" value={counts.NOT_FOUND} tone="not_found" delay={270} />
          </div>
        </div>
      </div>

      <div className="filter">
        <button className={`filter-btn ${!onlyIssues ? 'is-on' : ''}`} onClick={() => setOnlyIssues(false)}>
          All claims
        </button>
        <button className={`filter-btn ${onlyIssues ? 'is-on' : ''}`} onClick={() => setOnlyIssues(true)}>
          Issues only
        </button>
      </div>

      <div className="panel-scroll">
        <ul className="results">
          {rows.map((row, i) => (
            <ResultItem row={row} index={i} key={`${row.claim}-${i}`} />
          ))}
          {rows.length === 0 && (
            <li className="empty">
              {results.length === 0 ? 'No claims were checked.' : 'No issues. Every claim matched the code.'}
            </li>
          )}
        </ul>
      </div>
    </section>
  )
}

/** Shown in the scorecard slot until the Reporter finishes (or if the run stops early). */
export function ScorecardPlaceholder({ message, live }: { message: string; live: boolean }) {
  return (
    <section className="panel scorecard scorecard--placeholder" aria-label="Scorecard (pending)">
      <header className="panel-head">
        <h2 className="panel-title">Scorecard</h2>
      </header>
      <div className={`placeholder ${live ? 'is-live' : ''}`}>
        <div className="placeholder-ring" />
        <div className="placeholder-lines">
          <span />
          <span />
          <span />
        </div>
        <p className="placeholder-text">{message}</p>
      </div>
    </section>
  )
}

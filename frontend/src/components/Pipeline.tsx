import type { ReactNode } from 'react'
import type { AgentCounts } from '../lib/progress'
import type { AgentId, RunStatus } from '../lib/types'
import { AgentIcon } from './Icons'

const AGENTS: { id: AgentId; name: string; tech: string }[] = [
  { id: 'analyst', name: 'Paper Analyst', tech: 'Weaviate · hybrid' },
  { id: 'detective', name: 'Code Detective', tech: 'Qdrant · filters' },
  { id: 'critic', name: 'Critic', tech: 'Claude · structured' },
  { id: 'reporter', name: 'Reporter', tech: 'Scorecard' },
]

interface Props {
  active: AgentId | null
  status: RunStatus
  looping: boolean
  counts?: AgentCounts
  compact?: boolean
  /** When given, agents become buttons that open the inspector. */
  onSelect?: (agent: AgentId) => void
  selected?: AgentId | null
}

function countText(id: AgentId, counts: AgentCounts | undefined, status: RunStatus): string | null {
  if (!counts) return null
  switch (id) {
    case 'analyst':
      return counts.claims !== null ? `${counts.claims} claims` : null
    case 'detective':
      return counts.searches ? `${counts.searches} searches` : null
    case 'critic':
      return counts.verdicts ? `${counts.verdicts} verdicts` : null
    case 'reporter':
      return status === 'done' ? `${counts.issues} issue${counts.issues === 1 ? '' : 's'}` : null
  }
}

function AgentShell({ className, onClick, label, children }: { className: string; onClick?: () => void; label: string; children: ReactNode }) {
  if (!onClick) return <div className={className}>{children}</div>
  return (
    <button type="button" className={className} onClick={onClick} aria-label={label} title={label}>
      {children}
    </button>
  )
}

/** The four LangGraph agents: the active one glows, data flows along the arrows, and the retry loop lights up. */
export function Pipeline({ active, status, looping, counts, compact = false, onSelect, selected = null }: Props) {
  const activeIndex = active ? AGENTS.findIndex((a) => a.id === active) : -1
  const running = status === 'running'
  const done = status === 'done'
  const retries = counts?.retries ?? 0
  const loopLive = looping && running

  return (
    <section className={`pipeline ${running ? 'is-running' : ''} ${compact ? 'pipeline--compact' : ''}`} aria-label="Agent pipeline">
      {/* Critic -> Detective retry loop, drawn between the two agent icons */}
      <div className={`loop ${loopLive ? 'is-looping' : ''} ${retries > 0 ? 'has-retries' : ''}`} aria-hidden="true">
        <span className="loop-arrow" />
        <span className="loop-label">
          retry search{retries > 0 ? ` ×${retries}` : ''}
        </span>
      </div>

      {AGENTS.map((agent, i) => {
        const reached = done || (activeIndex >= 0 && i < activeIndex)
        const state = reached ? 'is-done' : running && i === activeIndex ? 'is-active' : ''
        const count = countText(agent.id, counts, status)
        return (
          <div className="pipeline-step" key={agent.id}>
            <AgentShell
              className={`agent ${state} ${onSelect ? 'agent--clickable' : ''} ${selected === agent.id ? 'is-selected' : ''}`}
              onClick={onSelect ? () => onSelect(agent.id) : undefined}
              label={`Inspect ${agent.name}`}
            >
              <div className="agent-icon">
                <AgentIcon agent={agent.id} />
                <span className="agent-pulse" />
              </div>
              <div className="agent-text">
                <div className="agent-name">{agent.name}</div>
                <div className="agent-tech">{agent.tech}</div>
                {count && (
                  <div className="agent-count" key={count}>
                    {count}
                  </div>
                )}
              </div>
            </AgentShell>
            {i < AGENTS.length - 1 && (
              <div className={`connector ${running && i < activeIndex ? 'is-flowing' : ''} ${reached && !running ? 'is-done' : ''}`}>
                <span className="connector-packet" />
                <span className="connector-packet connector-packet--late" />
                <span className="connector-head" />
              </div>
            )}
          </div>
        )
      })}
    </section>
  )
}

import type { AgentId } from '../lib/types'

const common = {
  width: 26,
  height: 26,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

export function AgentIcon({ agent }: { agent: AgentId }) {
  switch (agent) {
    case 'analyst':
      return (
        <svg {...common}>
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5M9 13h6M9 17h4" />
        </svg>
      )
    case 'detective':
      return (
        <svg {...common}>
          <circle cx="10.5" cy="10.5" r="6" />
          <path d="m15 15 5.5 5.5M8 10.5h5M10.5 8v5" />
        </svg>
      )
    case 'critic':
      return (
        <svg {...common}>
          <path d="M12 3v18M7 21h10M5 7h14" />
          <path d="m5 7-3 6a3 3 0 0 0 6 0zM19 7l-3 6a3 3 0 0 0 6 0z" />
        </svg>
      )
    case 'reporter':
      return (
        <svg {...common}>
          <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
        </svg>
      )
  }
}

export function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg {...common} width={18} height={18} className={`chevron ${open ? 'is-open' : ''}`}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}

export type VerdictStatus = 'MATCH' | 'MISMATCH' | 'NOT_FOUND'

/** One row of the final scorecard, as sent by the backend's last SSE event. */
export interface ResultRow {
  status: VerdictStatus
  claim: string
  paper: string
  code: string
  where: string
  quote: string
  section: string
}

export interface RunMeta {
  paper: { label: string; title: string; url: string | null; chunks: number }
  repo: { label: string; url: string | null; python_files: number; config_files: number; chunks: number }
}

export interface ClaimInfo {
  text: string
  category: string
  section: string
  quote: string
}

export interface PaperSectionHit {
  section: string
  score: number
  topics: string[]
  preview: string
}

export interface CodeHit {
  file_path: string
  start_line: number
  end_line: number
  name: string
  type: string
  score: number
}

/** Structured per-node data that comes with each step (newer backends only). */
export interface StepData {
  sections?: PaperSectionHit[]
  claim_count?: number
  query?: string
  attempt?: number
  hits?: CodeHit[]
  status?: VerdictStatus
  reason?: string
  paper_value?: string
  code_value?: string
  claim?: string
  where?: string
}

/** Everything the /verify stream can send. */
export type ServerEvent =
  | { type: 'status'; text: string }
  | ({ type: 'meta' } & RunMeta)
  | { type: 'step'; text: string; node?: string; data?: StepData }
  | { type: 'claims'; claims: ClaimInfo[] }
  | { type: 'report'; results: ResultRow[] }
  | { type: 'error'; message: string }

export type AgentId = 'analyst' | 'detective' | 'critic' | 'reporter'

export type StepKind = 'index' | 'analyst' | 'detective' | 'critic' | 'saved' | 'reporter'

export interface Step {
  id: number
  kind: StepKind
  text: string
  data?: StepData
}

export type RunStatus = 'idle' | 'running' | 'done' | 'error' | 'aborted'

export interface VerifyInput {
  paper: string
  repo: string
}

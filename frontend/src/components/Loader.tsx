/** Orbiting-rings loader with a checklist of ingestion steps (download, clone, index...). */
export function Loader({ statuses, active }: { statuses: string[]; active: boolean }) {
  const current = statuses.length - 1
  return (
    <div className="loader" role="status" aria-live="polite">
      <div className="loader-orbit">
        <span className="loader-ring loader-ring--1" />
        <span className="loader-ring loader-ring--2" />
        <span className="loader-ring loader-ring--3" />
        <span className="loader-core" />
      </div>
      <ol className="loader-steps">
        {statuses.length === 0 && <li className="loader-step is-current">Connecting to the backend</li>}
        {statuses.map((text, i) => {
          const isCurrent = i === current && active
          return (
            <li key={i} className={`loader-step ${isCurrent ? 'is-current' : 'is-done'}`}>
              <span className="loader-step-mark" aria-hidden="true">
                {isCurrent ? '' : '✓'}
              </span>
              {text}
              {isCurrent && (
                <span className="loader-dots" aria-hidden="true">
                  <span>.</span>
                  <span>.</span>
                  <span>.</span>
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}

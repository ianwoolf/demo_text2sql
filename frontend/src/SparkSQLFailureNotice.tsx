type Props = {
  status?: string
  explanation?: string
  missingInformation: string[]
  validationErrors: string[]
  busy: boolean
  onRetry: () => void
}

export function SparkSQLFailureNotice({
  status,
  explanation,
  missingInformation,
  validationErrors,
  busy,
  onRetry,
}: Props) {
  if (status !== 'insufficient_context' && status !== 'failed') return null

  const insufficient = status === 'insufficient_context'
  const details = insufficient ? missingInformation : validationErrors

  return (
    <div className="sql-failure-notice" role="alert">
      <div className="sql-failure-icon">!</div>
      <div className="sql-failure-content">
        <h3>{insufficient ? 'Insufficient metadata or source data' : 'Spark SQL validation failed'}</h3>
        {explanation?.trim() && <p>{explanation}</p>}
        {details.length > 0 && (
          <ul>{details.map(detail => <li key={detail}>{detail}</li>)}</ul>
        )}
        <p className="sql-failure-guidance">Review the requirement or Source Data, then try again.</p>
        <button type="button" disabled={busy} onClick={onRetry}>
          {busy ? 'Retrying…' : 'Retry Generation'}
        </button>
      </div>
    </div>
  )
}

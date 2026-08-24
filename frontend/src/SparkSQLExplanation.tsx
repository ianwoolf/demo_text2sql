type Props = {
  generationSource?: 'mock' | 'anthropic' | 'manual'
  status?: string
  explanation?: string
}

export function SparkSQLExplanation({generationSource, status, explanation}: Props) {
  if (generationSource !== 'anthropic' || status !== 'generated' || !explanation?.trim()) {
    return null
  }

  return (
    <section className="sql-explanation" aria-labelledby="sql-explanation-title">
      <h3 id="sql-explanation-title">LLM Explanation</h3>
      <p>{explanation}</p>
    </section>
  )
}

import {render, screen} from '@testing-library/react'
import {describe, expect, it} from 'vitest'
import {SparkSQLExplanation} from './SparkSQLExplanation'

describe('SparkSQLExplanation', () => {
  it('shows the explanation for a successful Anthropic generation', () => {
    render(
      <SparkSQLExplanation
        generationSource="anthropic"
        status="generated"
        explanation="Joins orders to customers, then aggregates completed sales by month and region."
      />,
    )

    expect(screen.getByRole('heading', {name: 'LLM Explanation'})).toBeInTheDocument()
    expect(screen.getByText(/Joins orders to customers/)).toBeInTheDocument()
  })

  it('does not show an explanation for mock, manual, or failed results', () => {
    const {rerender} = render(
      <SparkSQLExplanation generationSource="mock" status="generated" explanation="Mock details" />,
    )
    expect(screen.queryByRole('heading', {name: 'LLM Explanation'})).not.toBeInTheDocument()

    rerender(
      <SparkSQLExplanation generationSource="anthropic" status="failed" explanation="Failure details" />,
    )
    expect(screen.queryByRole('heading', {name: 'LLM Explanation'})).not.toBeInTheDocument()

    rerender(
      <SparkSQLExplanation generationSource="anthropic" status="generated" explanation="   " />,
    )
    expect(screen.queryByRole('heading', {name: 'LLM Explanation'})).not.toBeInTheDocument()
  })
})

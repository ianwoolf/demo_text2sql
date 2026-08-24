import {render, screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {describe, expect, it, vi} from 'vitest'
import {SparkSQLFailureNotice} from './SparkSQLFailureNotice'

describe('SparkSQLFailureNotice', () => {
  it('shows missing context details and retries generation', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(
      <SparkSQLFailureNotice
        status="insufficient_context"
        explanation="A customer region column is required."
        missingInformation={['customers.region metadata']}
        validationErrors={[]}
        busy={false}
        onRetry={onRetry}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Insufficient metadata or source data')
    expect(screen.getByRole('alert')).toHaveTextContent('customers.region metadata')
    await user.click(screen.getByRole('button', {name: 'Retry Generation'}))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('shows SQL validation errors for a failed result', () => {
    render(
      <SparkSQLFailureNotice
        status="failed"
        explanation="The generated query did not pass validation."
        missingInformation={[]}
        validationErrors={['Only selected source tables may be referenced.']}
        busy={false}
        onRetry={() => undefined}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Spark SQL validation failed')
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Only selected source tables may be referenced.',
    )
  })
})

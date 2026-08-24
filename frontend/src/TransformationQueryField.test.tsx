import {render, screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {describe, expect, it, vi} from 'vitest'
import {TransformationQueryField} from './TransformationQueryField'

describe('TransformationQueryField', () => {
  it('fills the query with the inline example', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TransformationQueryField value="" onChange={onChange} />)

    await user.click(screen.getByRole('button', {name: 'Use example'}))

    expect(onChange).toHaveBeenCalledWith(
      'Calculate completed monthly sales and distinct customer count by region.',
    )
  })
})

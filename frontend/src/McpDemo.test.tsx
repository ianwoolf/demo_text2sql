import {render, screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {describe, expect, it, vi} from 'vitest'
import {DemoScenarioGrid, MCP_DEMO_SCENARIOS, McpHistoryConversation} from './McpDemo'

describe('DemoScenarioGrid', () => {
  it('shows six analysis and orchestration scenarios', () => {
    render(<DemoScenarioGrid onSelect={() => undefined} />)

    expect(screen.getAllByRole('button')).toHaveLength(6)
    expect(screen.getByRole('button', {name: /Build a monthly sales dataset/})).toHaveTextContent(
      '5 MCPs',
    )
    expect(new Set(MCP_DEMO_SCENARIOS.map(item => item.category))).toEqual(
      new Set(['Analytics', 'Data Engineering', 'Operations']),
    )
  })

  it('returns the selected scenario', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<DemoScenarioGrid onSelect={onSelect} />)

    await user.click(screen.getByRole('button', {name: /Build a monthly sales dataset/}))

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({id: 'build-monthly-sales', mode: 'history'}),
    )
  })
})

describe('McpHistoryConversation', () => {
  it('shows a multi-turn conversation that gates MCP calls on user confirmations', () => {
    const {container} = render(<McpHistoryConversation />)

    expect(screen.getAllByRole('group', {name: 'User message'})).toHaveLength(4)
    expect(screen.getAllByRole('article', {name: /Chatbot response/})).toHaveLength(4)
    expect([...container.querySelectorAll('[data-mcp]')].map(item => item.getAttribute('data-mcp'))).toEqual([
      'Knowledge Base MCP',
      'Metadata MCP',
      'Text2SQL MCP',
      'Query Engine MCP',
      'SparkJobRunner MCP',
      'SparkJobRunner MCP',
      'Airflow MCP',
    ])
    expect(screen.getByText('Please confirm these business and delivery settings.')).toBeInTheDocument()
    expect(screen.getByText('Approve this SQL and preview?')).toBeInTheDocument()
    expect(screen.getByText('Goal completed')).toBeInTheDocument()
    expect(screen.getByText('sales_monthly_pipeline')).toBeInTheDocument()
  })
})

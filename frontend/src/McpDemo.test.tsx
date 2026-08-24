import {render, screen, within} from '@testing-library/react'
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
  it('shows the complete ordered multi-MCP workflow', () => {
    render(<McpHistoryConversation />)

    const timeline = screen.getByRole('list', {name: 'MCP execution timeline'})
    expect(within(timeline).getAllByRole('listitem').map(item => item.getAttribute('data-mcp'))).toEqual([
      'Knowledge Base MCP',
      'Metadata MCP',
      'Text2SQL MCP',
      'Query Engine MCP',
      'SparkJobRunner MCP',
      'Airflow MCP',
    ])
    expect(screen.getAllByText('Waiting for approval')).toHaveLength(2)
    expect(screen.getByText('sales_monthly_pipeline')).toBeInTheDocument()
  })
})

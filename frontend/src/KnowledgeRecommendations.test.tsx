import {render, screen, within} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {describe, expect, it} from 'vitest'
import {KnowledgeRecommendations, applyRecommendationSources} from './KnowledgeRecommendationPanel'
import {MOCK_KNOWLEDGE_RECOMMENDATIONS, type ResolvedRecommendationSources} from './knowledgeRecommendations'

const regionalJob = {...MOCK_KNOWLEDGE_RECOMMENDATIONS[0], similarity: 92}

describe('KnowledgeRecommendations', () => {
  it('shows recommendation summaries and opens the full snapshot', async () => {
    const user = userEvent.setup()
    render(
      <KnowledgeRecommendations
        query="monthly sales"
        items={[regionalJob]}
        onUseSources={() => undefined}
        availableTables={['orders', 'customers']}
      />,
    )

    expect(screen.getByRole('button', {name: /monthly regional sales/i})).toBeVisible()
    await user.click(screen.getByRole('button', {name: /monthly regional sales/i}))

    const dialog = screen.getByRole('dialog', {name: /monthly regional sales details/i})
    expect(within(dialog).getByText('demo_sales.orders')).toBeVisible()
    expect(within(dialog).getByText(/date_format\(o\.order_date/i)).toBeVisible()
    expect(within(dialog).getByText('analytics.sales.monthly_region_sales')).toBeVisible()
  })

  it('passes only resolved source selection when Use Sources is chosen', async () => {
    const user = userEvent.setup()
    let received: ResolvedRecommendationSources | undefined
    render(
      <KnowledgeRecommendations
        query="monthly sales"
        items={[regionalJob]}
        onUseSources={resolved => { received = resolved }}
        availableTables={['orders', 'customers']}
      />,
    )

    await user.click(screen.getByRole('button', {name: /monthly regional sales/i}))
    await user.click(screen.getByRole('button', {name: 'Use Sources'}))

    expect(received).toEqual({selected: ['orders', 'customers'], primary: 'orders', missing: []})
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows an instruction instead of recommendations for an empty query', () => {
    render(
      <KnowledgeRecommendations
        query=""
        items={[]}
        onUseSources={() => undefined}
        availableTables={['orders']}
      />,
    )

    expect(screen.getByText(/describe the transformation/i)).toBeVisible()
  })
})

describe('applyRecommendationSources', () => {
  it('applies only sources, clears stale SQL, and preserves requirement and sink', () => {
    const current = {
      selected: ['products'],
      primary: 'products',
      sql: {content: 'SELECT * FROM products'},
      name: 'Current request',
      requirement: 'Current natural language query',
      sink: {catalog: 'analytics', database: 'sales', table: 'current_sink'},
    }

    expect(
      applyRecommendationSources(current, {
        selected: ['orders', 'customers'],
        primary: 'orders',
        missing: [],
      }),
    ).toEqual({
      ...current,
      selected: ['orders', 'customers'],
      primary: 'orders',
      sql: null,
    })
  })
})

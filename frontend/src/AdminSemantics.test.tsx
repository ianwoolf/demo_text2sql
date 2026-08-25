import {render, screen, within} from '@testing-library/react'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import {Admin} from './App'
import {api} from './api'

vi.mock('./api', () => ({api: vi.fn()}))

const catalog = {
  name: 'Sales Analytics Demo',
  schema_name: 'demo_sales',
  relations: [],
  tables: [
    {name: 'orders', description: 'Sales orders', owner: 'Sales Operations', data_tier: 'T1', columns: []},
    {name: 'customers', description: 'Customer master data', owner: 'CRM Team', data_tier: 'T2', columns: []},
    {name: 'products', description: 'Product catalog', owner: 'Merchandising', data_tier: 'T2', columns: []},
    {name: 'order_items', description: 'Order line items', owner: 'Commerce Platform', data_tier: 'T1', columns: []},
  ],
}

describe('Data & Semantics admin page', () => {
  beforeEach(() => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path.endsWith('/metadata')) return catalog
      if (path.endsWith('/semantics')) return {instructions: [], terms: [], metrics: [], joins: [], examples: []}
      if (path === '/reviews') return []
      if (path === '/benchmarks') return {}
      throw new Error(`Unexpected API path: ${path}`)
    })
  })

  it('groups datasets by domain and shows their governance and user access', async () => {
    render(<Admin space={{id: 'sales-demo', name: 'Sales Analytics', description: '', provider_type: 'local', target_type: 'mock'}} section="semantics" />)

    const salesDomain = await screen.findByRole('region', {name: 'Sales Operations domain'})
    expect(within(salesDomain).getByText('orders')).toBeInTheDocument()
    expect(within(salesDomain).getByText('order_items')).toBeInTheDocument()
    expect(screen.getByRole('region', {name: 'Customer domain'})).toHaveTextContent('customers')
    expect(screen.getByRole('region', {name: 'Product domain'})).toHaveTextContent('products')
    expect(screen.getAllByText('T1 · Raw')).toHaveLength(2)
    expect(screen.getByRole('heading', {name: 'User Access'})).toBeInTheDocument()
    expect(screen.getByText('Alex Morgan')).toBeInTheDocument()
    expect(screen.getByText('Data Administrators')).toBeInTheDocument()
  })
})

export type RecommendationKind = 'online_job' | 'history'
export type RecommendationSource = {datasetId: string; role: 'primary' | 'auxiliary'}
export type RecommendationSink = {
  catalog: string
  database: string
  table: string
  writeMode: 'append' | 'overwrite'
}
export type KnowledgeRecommendation = {
  id: string
  kind: RecommendationKind
  title: string
  requirement: string
  keywords: string[]
  baseline: number
  sources: RecommendationSource[]
  sparkSql: string
  sink: RecommendationSink
  status: string
  schedule?: string
  lastRun?: string
  lastUsed?: string
}
export type ScoredRecommendation = KnowledgeRecommendation & {similarity: number}
export type ResolvedRecommendationSources = {selected: string[]; primary: string; missing: string[]}

export function deriveRequestName(question: string): string {
  return question.trim().slice(0, 60) || 'Untitled transformation'
}

export const MOCK_KNOWLEDGE_RECOMMENDATIONS: KnowledgeRecommendation[] = [
  {
    id: 'job-monthly-regional-sales',
    kind: 'online_job',
    title: 'Monthly regional sales',
    requirement: 'Calculate completed monthly sales and distinct customer count by region.',
    keywords: ['monthly', 'sales', 'region', 'regional', 'customer', 'completed'],
    baseline: 58,
    sources: [
      {datasetId: 'demo_sales.orders', role: 'primary'},
      {datasetId: 'demo_sales.customers', role: 'auxiliary'},
    ],
    sparkSql: `SELECT
  date_format(o.order_date, 'yyyy-MM') AS month,
  c.region,
  SUM(o.total_amount) AS sales,
  COUNT(DISTINCT o.customer_id) AS customer_count
FROM demo_sales.orders o
JOIN demo_sales.customers c ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
GROUP BY date_format(o.order_date, 'yyyy-MM'), c.region`,
    sink: {catalog: 'analytics', database: 'sales', table: 'monthly_region_sales', writeMode: 'overwrite'},
    status: 'Healthy',
    schedule: 'Every day · 02:00 UTC',
    lastRun: 'Today · 02:04 UTC',
  },
  {
    id: 'job-product-revenue-daily',
    kind: 'online_job',
    title: 'Daily product revenue',
    requirement: 'Aggregate completed order revenue and units by product category each day.',
    keywords: ['daily', 'product', 'category', 'revenue', 'units', 'completed'],
    baseline: 51,
    sources: [
      {datasetId: 'demo_sales.order_items', role: 'primary'},
      {datasetId: 'demo_sales.orders', role: 'auxiliary'},
      {datasetId: 'demo_sales.products', role: 'auxiliary'},
    ],
    sparkSql: `SELECT
  to_date(o.order_date) AS order_day,
  p.category,
  SUM(oi.quantity * oi.unit_price) AS revenue,
  SUM(oi.quantity) AS units
FROM demo_sales.order_items oi
JOIN demo_sales.orders o ON oi.order_id = o.order_id
JOIN demo_sales.products p ON oi.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY to_date(o.order_date), p.category`,
    sink: {catalog: 'analytics', database: 'product', table: 'daily_category_revenue', writeMode: 'overwrite'},
    status: 'Healthy',
    schedule: 'Every day · 03:30 UTC',
    lastRun: 'Today · 03:36 UTC',
  },
  {
    id: 'history-customer-order-frequency',
    kind: 'history',
    title: 'Customer order frequency',
    requirement: 'Summarize order frequency and lifetime sales for each customer.',
    keywords: ['customer', 'order', 'frequency', 'lifetime', 'sales', 'segment'],
    baseline: 47,
    sources: [
      {datasetId: 'demo_sales.customers', role: 'primary'},
      {datasetId: 'demo_sales.orders', role: 'auxiliary'},
    ],
    sparkSql: `SELECT
  c.customer_id,
  c.region,
  COUNT(o.order_id) AS order_count,
  SUM(o.total_amount) AS lifetime_sales
FROM demo_sales.customers c
LEFT JOIN demo_sales.orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.region`,
    sink: {catalog: 'analytics', database: 'customer', table: 'customer_order_frequency', writeMode: 'overwrite'},
    status: 'Success',
    lastUsed: 'Yesterday · 16:42 UTC',
  },
  {
    id: 'history-refund-impact',
    kind: 'history',
    title: 'Refund impact by region',
    requirement: 'Measure refunded order value and refund rate by customer region.',
    keywords: ['refund', 'refunded', 'impact', 'rate', 'region', 'order'],
    baseline: 44,
    sources: [
      {datasetId: 'demo_sales.orders', role: 'primary'},
      {datasetId: 'demo_sales.customers', role: 'auxiliary'},
    ],
    sparkSql: `SELECT
  c.region,
  SUM(CASE WHEN o.status = 'refunded' THEN o.total_amount ELSE 0 END) AS refunded_value,
  AVG(CASE WHEN o.status = 'refunded' THEN 1.0 ELSE 0.0 END) AS refund_rate
FROM demo_sales.orders o
JOIN demo_sales.customers c ON o.customer_id = c.customer_id
GROUP BY c.region`,
    sink: {catalog: 'analytics', database: 'risk', table: 'regional_refund_impact', writeMode: 'overwrite'},
    status: 'Success',
    lastUsed: '4 days ago',
  },
  {
    id: 'history-category-customer-mix',
    kind: 'history',
    title: 'Category customer mix',
    requirement: 'Count distinct customers and orders by product category.',
    keywords: ['category', 'customer', 'product', 'order', 'mix', 'distinct'],
    baseline: 42,
    sources: [
      {datasetId: 'demo_sales.order_items', role: 'primary'},
      {datasetId: 'demo_sales.orders', role: 'auxiliary'},
      {datasetId: 'demo_sales.products', role: 'auxiliary'},
    ],
    sparkSql: `SELECT
  p.category,
  COUNT(DISTINCT o.customer_id) AS customer_count,
  COUNT(DISTINCT o.order_id) AS order_count
FROM demo_sales.order_items oi
JOIN demo_sales.orders o ON oi.order_id = o.order_id
JOIN demo_sales.products p ON oi.product_id = p.product_id
GROUP BY p.category`,
    sink: {catalog: 'analytics', database: 'product', table: 'category_customer_mix', writeMode: 'overwrite'},
    status: 'Success',
    lastUsed: '2 weeks ago',
  },
]

function tokens(value: string): Set<string> {
  return new Set(value.toLowerCase().match(/[a-z0-9]+/g) ?? [])
}

export function recommendKnowledge(
  query: string,
  items: KnowledgeRecommendation[] = MOCK_KNOWLEDGE_RECOMMENDATIONS,
  limit = 4,
): ScoredRecommendation[] {
  const queryTokens = tokens(query)
  if (!query.trim() || queryTokens.size === 0) return []

  return items
    .map(item => {
      const searchable = tokens(`${item.title} ${item.requirement} ${item.keywords.join(' ')}`)
      const overlap = [...queryTokens].filter(token => searchable.has(token)).length
      const overlapRatio = overlap / queryTokens.size
      const similarity = Math.min(99, Math.round(item.baseline + overlapRatio * 40))
      return {...item, similarity}
    })
    .sort((left, right) => right.similarity - left.similarity || left.id.localeCompare(right.id))
    .slice(0, Math.max(0, limit))
}

function tableName(datasetId: string): string {
  return datasetId.split('.').at(-1) ?? datasetId
}

export function resolveRecommendationSources(
  recommendation: KnowledgeRecommendation,
  availableTables: string[],
): ResolvedRecommendationSources {
  const available = new Set(availableTables)
  const sourceNames = recommendation.sources.map(source => ({...source, table: tableName(source.datasetId)}))
  const selected = sourceNames.filter(source => available.has(source.table)).map(source => source.table)
  const missing = sourceNames.filter(source => !available.has(source.table)).map(source => source.table)
  const recommendedPrimary = sourceNames.find(source => source.role === 'primary')?.table ?? ''

  return {
    selected,
    primary: selected.includes(recommendedPrimary) ? recommendedPrimary : (selected[0] ?? ''),
    missing,
  }
}

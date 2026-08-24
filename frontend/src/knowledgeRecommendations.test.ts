import {describe, expect, it} from 'vitest'
import {
  MOCK_KNOWLEDGE_RECOMMENDATIONS,
  deriveRequestName,
  recommendKnowledge,
  resolveRecommendationSources,
} from './knowledgeRecommendations'

describe('deriveRequestName', () => {
  it('creates a compact request name from the user question', () => {
    expect(deriveRequestName('  Calculate completed monthly sales by region.  ')).toBe(
      'Calculate completed monthly sales by region.',
    )
    expect(deriveRequestName('x'.repeat(70))).toBe('x'.repeat(60))
    expect(deriveRequestName('   ')).toBe('Untitled transformation')
  })
})

describe('recommendKnowledge', () => {
  it('returns no recommendations for an empty requirement', () => {
    expect(recommendKnowledge('   ')).toEqual([])
  })

  it('ranks the matching regional sales job first', () => {
    const results = recommendKnowledge('Calculate monthly sales by region')

    expect(results[0]).toMatchObject({id: 'job-monthly-regional-sales', kind: 'online_job'})
    expect(results[0].similarity).toBeGreaterThan(results[1].similarity)
  })

  it('returns at most four recommendations in descending score order', () => {
    const results = recommendKnowledge('customer order product revenue trend')

    expect(results).toHaveLength(4)
    expect(results.map(item => item.similarity)).toEqual(
      [...results.map(item => item.similarity)].sort((a, b) => b - a),
    )
  })

  it('exposes both online jobs and history in the mock catalog', () => {
    expect(new Set(MOCK_KNOWLEDGE_RECOMMENDATIONS.map(item => item.kind))).toEqual(
      new Set(['online_job', 'history']),
    )
  })
})

describe('resolveRecommendationSources', () => {
  it('resolves available recommendation sources and their primary role', () => {
    const recommendation = MOCK_KNOWLEDGE_RECOMMENDATIONS[0]

    expect(resolveRecommendationSources(recommendation, ['orders', 'customers', 'products'])).toEqual({
      selected: ['orders', 'customers'],
      primary: 'orders',
      missing: [],
    })
  })

  it('skips missing sources and deterministically falls back to the first available primary', () => {
    const recommendation = {
      ...MOCK_KNOWLEDGE_RECOMMENDATIONS[0],
      sources: [
        {datasetId: 'demo_sales.orders', role: 'primary' as const},
        {datasetId: 'demo_sales.customers', role: 'auxiliary' as const},
      ],
    }

    expect(resolveRecommendationSources(recommendation, ['customers'])).toEqual({
      selected: ['customers'],
      primary: 'customers',
      missing: ['orders'],
    })
  })
})

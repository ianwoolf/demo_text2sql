# Knowledge Recommendations UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorder and compact the Data Transformation workspace, add mocked knowledge recommendations with full snapshot details, and let users apply only a recommendation's source datasets.

**Architecture:** Keep recommendation fixtures and deterministic matching/source resolution in a pure TypeScript module. Render recommendation cards and their detail dialog as focused React components, while `TransformationBuilder` remains the owner of request state and applies the source-only transition. Use Vitest and Testing Library for behavior-focused unit and component tests.

**Tech Stack:** React 19, TypeScript 5.8, Vite 7, Vitest, Testing Library, CSS

**Spec:** `docs/superpowers/specs/2026-08-23-knowledge-recommendations-ui-design.md`

## Global Constraints

- All visible product copy remains English.
- Recommendation lookup is frontend-only mock behavior; no backend endpoint is added.
- `Use Sources` replaces selected sources and primary source, clears generated Spark SQL, and preserves request name, requirement, and sink.
- Existing Anthropic generation, SQLGlot validation, task submission, dataset picker, and dataset detail behavior remain intact.
- The transformation layout becomes approximately 15–20 percent denser while retaining practical click targets and labels.

---

### Task 1: Recommendation Matching and Source Resolution

**Files:**
- Create: `frontend/src/knowledgeRecommendations.ts`
- Create: `frontend/src/knowledgeRecommendations.test.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/vite.config.ts`

**Interfaces:**
- Produces: `KnowledgeRecommendation`, `RecommendationSource`, `RecommendationSink`, `MOCK_KNOWLEDGE_RECOMMENDATIONS`
- Produces: `recommendKnowledge(query: string, items?: KnowledgeRecommendation[], limit?: number): ScoredRecommendation[]`
- Produces: `resolveRecommendationSources(recommendation: KnowledgeRecommendation, availableTables: string[]): {selected: string[]; primary: string; missing: string[]}`

- [ ] **Step 1: Add the frontend test runner**

Add these development dependencies with `npm install --save-dev vitest@^3.2.4 @testing-library/react@^16.3.0 @testing-library/jest-dom@^6.6.3 @testing-library/user-event@^14.6.1 jsdom@^26.1.0`, add `"test": "vitest run"` to `scripts`, change the `defineConfig` import to `vitest/config`, and configure Vite with `test: {environment: 'jsdom', setupFiles: './src/testSetup.ts'}`. Create `frontend/src/testSetup.ts` importing `@testing-library/jest-dom/vitest`.

- [ ] **Step 2: Write failing matching tests**

Create literal fixtures and assertions proving these breaks are caught: an empty query incorrectly returning suggestions, keyword overlap ranking a nonmatching job first, more than four results escaping the limit, and score order being unstable.

```ts
import {describe, expect, it} from 'vitest'
import {MOCK_KNOWLEDGE_RECOMMENDATIONS, recommendKnowledge} from './knowledgeRecommendations'

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
    expect(results.map(item => item.similarity)).toEqual([...results.map(item => item.similarity)].sort((a, b) => b - a))
  })

  it('exposes both online jobs and history in the mock catalog', () => {
    expect(new Set(MOCK_KNOWLEDGE_RECOMMENDATIONS.map(item => item.kind))).toEqual(new Set(['online_job', 'history']))
  })
})
```

- [ ] **Step 3: Run the tests and verify RED**

Run: `cd frontend && npm test -- knowledgeRecommendations.test.ts`

Expected: FAIL because `knowledgeRecommendations.ts` and its exported behavior do not exist.

- [ ] **Step 4: Implement deterministic recommendation matching**

Create five complete mock snapshots using the existing metadata table names (`orders`, `customers`, `products`, `order_items`). Normalize queries with lowercase alphanumeric tokens, calculate keyword overlap, combine overlap with a 0–100 baseline, clamp the displayed similarity, sort by similarity then stable ID, and slice to the requested limit. Include Spark SQL and sink snapshots in every fixture.

```ts
export type RecommendationKind = 'online_job' | 'history'
export type RecommendationSource = {datasetId: string; role: 'primary' | 'auxiliary'}
export type RecommendationSink = {catalog: string; database: string; table: string; writeMode: 'append' | 'overwrite'}
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
```

- [ ] **Step 5: Write failing source-resolution tests**

```ts
import {resolveRecommendationSources} from './knowledgeRecommendations'

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
```

- [ ] **Step 6: Run the source-resolution tests and verify RED**

Run: `cd frontend && npm test -- knowledgeRecommendations.test.ts`

Expected: FAIL because `resolveRecommendationSources` is not exported.

- [ ] **Step 7: Implement source resolution and verify GREEN**

Resolve the table name as the final segment of each `datasetId`, preserve snapshot order, filter against `availableTables`, report missing names, retain the recommended primary when present, and otherwise choose `selected[0] || ''`.

Run: `cd frontend && npm test -- knowledgeRecommendations.test.ts`

Expected: PASS.

- [ ] **Step 8: Commit the pure recommendation layer**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/testSetup.ts frontend/src/knowledgeRecommendations.ts frontend/src/knowledgeRecommendations.test.ts
git commit -m "feat: add knowledge recommendation matching"
```

---

### Task 2: Recommendation Cards, Detail Dialog, and Source-Only Application

**Files:**
- Create: `frontend/src/KnowledgeRecommendations.tsx`
- Create: `frontend/src/KnowledgeRecommendations.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `ScoredRecommendation` and `resolveRecommendationSources` from `knowledgeRecommendations.ts`
- Produces: `KnowledgeRecommendations({query, items, availableTables, onUseSources})`
- Produces: `KnowledgeRecommendationModal({item, availableTables, onClose, onUseSources})`
- Produces: `applyRecommendationSources(current, resolved)` as a pure state transition that preserves `name`, `requirement`, and `sink` while setting `sql: null`

- [ ] **Step 1: Write failing component tests for recommendation display and details**

Render real components with literal recommendation data. Assert user-visible behavior rather than implementation structure.

```tsx
it('shows recommendation summaries and opens the full snapshot', async () => {
  const user = userEvent.setup()
  render(<KnowledgeRecommendations query="monthly sales" items={[regionalJob]} onUseSources={() => {}} availableTables={['orders', 'customers']} />)
  expect(screen.getByRole('button', {name: /monthly regional sales/i})).toBeVisible()
  await user.click(screen.getByRole('button', {name: /monthly regional sales/i}))
  const dialog = screen.getByRole('dialog', {name: /monthly regional sales details/i})
  expect(within(dialog).getByText('demo_sales.orders')).toBeVisible()
  expect(within(dialog).getByText(/SELECT/i)).toBeVisible()
  expect(within(dialog).getByText('analytics.sales.monthly_region_sales')).toBeVisible()
})
```

- [ ] **Step 2: Run the component test and verify RED**

Run: `cd frontend && npm test -- KnowledgeRecommendations.test.tsx`

Expected: FAIL because the recommendation components do not exist.

- [ ] **Step 3: Implement recommendation cards and detail dialog**

Render up to four cards with type, title, similarity, source count, and schedule/last-used metadata. Keep modal state inside `KnowledgeRecommendations`. The modal renders requirement, sources with roles, SQL, sink, status, schedule/last-run fields, missing-source warning, close button, and `Use Sources`. Disable the action only when resolved `selected` is empty.

- [ ] **Step 4: Verify recommendation components GREEN**

Run: `cd frontend && npm test -- KnowledgeRecommendations.test.tsx`

Expected: PASS.

- [ ] **Step 5: Write the failing source-only state-transition test**

Export and test a pure transition so the preservation contract cannot be hidden behind React state timing.

```ts
it('applies only sources, clears stale SQL, and preserves requirement and sink', () => {
  const current = {
    selected: ['products'],
    primary: 'products',
    sql: generatedSql,
    name: 'Current request',
    requirement: 'Current natural language query',
    sink: currentSink,
  }
  expect(applyRecommendationSources(current, {selected: ['orders', 'customers'], primary: 'orders', missing: []})).toEqual({
    ...current,
    selected: ['orders', 'customers'],
    primary: 'orders',
    sql: null,
  })
})
```

- [ ] **Step 6: Run the transition test and verify RED**

Run: `cd frontend && npm test -- KnowledgeRecommendations.test.tsx`

Expected: FAIL because `applyRecommendationSources` does not exist.

- [ ] **Step 7: Implement and integrate the source-only transition**

Add the pure transition beside the recommendation components. In `TransformationBuilder`, compute recommendations from `requirement`, render the recommendation section directly below the step-1 fields, and apply the returned `selected` and `primary` values while setting `sql` to `null`. Do not call the request-name, requirement, or sink setters in this action.

- [ ] **Step 8: Reorder the transformation stages**

Change progress labels and panels to:

1. Transformation Requirement
2. Source Data
3. Generated Spark SQL
4. Sink Dataset

Keep `Generate Spark SQL` after the source panel so the button remains adjacent to the inputs it needs. Preserve all existing generation, validation, picker, detail, sink, and request-creation handlers.

- [ ] **Step 9: Run focused and complete frontend tests**

Run: `cd frontend && npm test -- KnowledgeRecommendations.test.tsx`

Expected: PASS.

Run: `cd frontend && npm test`

Expected: all frontend tests PASS.

- [ ] **Step 10: Commit recommendation interaction**

```bash
git add frontend/src/App.tsx frontend/src/KnowledgeRecommendations.tsx frontend/src/KnowledgeRecommendations.test.tsx
git commit -m "feat: add source-only knowledge recommendations"
```

---

### Task 3: Brighter Technical Theme and Compact Responsive Layout

**Files:**
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: existing semantic class names plus `.knowledge-recommendations`, `.recommendation-grid`, `.recommendation-card`, and `.recommendation-modal`
- Produces: responsive desktop, tablet, and narrow-screen presentation without behavioral changes

- [ ] **Step 1: Establish baseline verification before styling**

Run: `cd frontend && npm test && npm run build`

Expected: tests PASS and Vite production build succeeds before CSS changes.

- [ ] **Step 2: Apply the bright technical palette**

Introduce CSS custom properties for blue-slate text/sidebar, electric-blue primary actions, teal success states, violet/cyan recommendation badges, cold-white surfaces, pale blue-gray backgrounds, borders, focus rings, and shadows. Replace transformation and shared navigation green/lime values with these variables while retaining error/warning semantics.

- [ ] **Step 3: Reduce sidebar typography and navigation density**

Set navigation labels to 12–13 px with weight 400/500, reduce navigation row height and icon size, and use a translucent blue active background with a narrow blue accent. Keep workspace and profile names readable and preserve the collapsed responsive sidebar behavior.

- [ ] **Step 4: Compact the transformation workspace**

Reduce panel padding, inter-panel gaps, progress-strip height, field padding, selected-source row height, SQL empty-state height, and heading size by approximately 15–20 percent. Keep interactive buttons at least 32 px high and modal controls comfortably clickable.

- [ ] **Step 5: Style recommendation summaries and modal responsively**

Use a dense two-column card grid on desktop, one column below 900 px, distinct Online Job/History badges, a compact snapshot grid, readable monospace SQL, explicit missing-source warning, and a sticky or consistently visible modal action row. At narrow widths, stack metadata without horizontal page overflow.

- [ ] **Step 6: Run automated regression verification**

Run: `cd frontend && npm test && npm run build`

Expected: all frontend tests PASS and Vite build succeeds without TypeScript errors.

Run: `cd backend && .venv/bin/pytest -q`

Expected: all backend regression tests PASS.

- [ ] **Step 7: Perform browser smoke verification**

At `http://127.0.0.1:5173/`, verify:

- the progress strip and panels use Requirement → Source Data → Spark SQL → Sink Dataset;
- typing a regional-sales requirement ranks the regional job first;
- a recommendation opens a modal containing source, SQL, and sink;
- `Use Sources` replaces only source rows and clears visible generated SQL;
- the requirement text and sink values remain unchanged;
- source Add and dataset-detail modals still work;
- sidebar labels are smaller/lighter and the page remains usable at desktop and narrow viewport widths.

- [ ] **Step 8: Commit the visual redesign**

```bash
git add frontend/src/styles.css
git commit -m "style: brighten and compact data workspace"
```

---

### Task 4: Final Verification and Documentation Check

**Files:**
- Modify: `README.md` only if the visible workflow description still lists Source before Requirement

**Interfaces:**
- Consumes: completed frontend feature and existing documented Spark SQL workflow
- Produces: a verified repository state with documentation matching the UI order

- [ ] **Step 1: Check the README workflow wording**

Compare the transformation UI section with the implemented Requirement → Source Data → Spark SQL → Sink Dataset order. If it names the old order, update only that wording; keep the documented metadata, LLM, SQLGlot, approval, and SparkJobRunner flow unchanged.

- [ ] **Step 2: Run the complete verification set from the repository root**

Run: `cd frontend && npm test && npm run build`

Expected: all frontend tests PASS and build succeeds.

Run: `cd backend && .venv/bin/pytest -q`

Expected: all backend tests PASS.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 3: Review the final diff for scope and secrets**

Run: `git status --short && git diff --stat HEAD && git diff HEAD -- . ':!.env'`

Confirm only the planned UI, tests, dependency metadata, and any necessary README wording changed; confirm no `.env`, API key, authorization header, or LLM credential appears in the diff.

- [ ] **Step 4: Commit documentation adjustment if needed**

```bash
git add README.md
git commit -m "docs: align transformation workflow order"
```

Skip this commit when README required no change.

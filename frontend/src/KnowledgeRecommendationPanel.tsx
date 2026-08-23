import {useState} from 'react'
import {
  resolveRecommendationSources,
  type ResolvedRecommendationSources,
  type ScoredRecommendation,
} from './knowledgeRecommendations'

type KnowledgeRecommendationProps = {
  query: string
  items: ScoredRecommendation[]
  availableTables: string[]
  onUseSources: (resolved: ResolvedRecommendationSources) => void
}

type RecommendationState<TSql, TSink> = {
  selected: string[]
  primary: string
  sql: TSql | null
  name: string
  requirement: string
  sink: TSink
}

export function applyRecommendationSources<TSql, TSink>(
  current: RecommendationState<TSql, TSink>,
  resolved: ResolvedRecommendationSources,
): RecommendationState<TSql, TSink> {
  return {...current, selected: resolved.selected, primary: resolved.primary, sql: null}
}

function kindLabel(kind: ScoredRecommendation['kind']): string {
  return kind === 'online_job' ? 'Online Job' : 'History'
}

function RecommendationModal({
  item,
  availableTables,
  onClose,
  onUseSources,
}: {
  item: ScoredRecommendation
  availableTables: string[]
  onClose: () => void
  onUseSources: (resolved: ResolvedRecommendationSources) => void
}) {
  const resolved = resolveRecommendationSources(item, availableTables)
  const sinkName = `${item.sink.catalog}.${item.sink.database}.${item.sink.table}`

  function closeBackdrop(event: React.MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) onClose()
  }

  function apply() {
    if (!resolved.selected.length) return
    onUseSources(resolved)
    onClose()
  }

  return <div className="source-modal-backdrop recommendation-backdrop" onClick={closeBackdrop}>
    <div
      className="recommendation-modal"
      role="dialog"
      aria-modal="true"
      aria-label={`${item.title} details`}
    >
      <header className="recommendation-modal-head">
        <div>
          <div className="recommendation-modal-tags">
            <span className={`recommendation-kind ${item.kind}`}>{kindLabel(item.kind)}</span>
            <span className="recommendation-score">{item.similarity}% match</span>
          </div>
          <h2>{item.title}</h2>
          <p>{item.requirement}</p>
        </div>
        <button aria-label="Close recommendation details" onClick={onClose}>×</button>
      </header>

      <div className="recommendation-operational">
        <span><small>Status</small><b>{item.status}</b></span>
        {item.schedule && <span><small>Schedule</small><b>{item.schedule}</b></span>}
        {item.lastRun && <span><small>Last run</small><b>{item.lastRun}</b></span>}
        {item.lastUsed && <span><small>Last used</small><b>{item.lastUsed}</b></span>}
      </div>

      {resolved.missing.length > 0 && <div className="recommendation-warning">
        {resolved.selected.length
          ? `Unavailable sources will be skipped: ${resolved.missing.join(', ')}`
          : `None of this recommendation's sources are available: ${resolved.missing.join(', ')}`}
      </div>}

      <section className="recommendation-snapshot">
        <div className="recommendation-snapshot-head"><span>01</span><h3>Source snapshot</h3></div>
        <div className="recommendation-source-list">
          {item.sources.map(source => <div key={source.datasetId}>
            <code>{source.datasetId}</code>
            <span className={`source-role ${source.role}`}>{source.role}</span>
          </div>)}
        </div>
      </section>

      <section className="recommendation-snapshot">
        <div className="recommendation-snapshot-head"><span>02</span><h3>Spark SQL snapshot</h3></div>
        <pre className="recommendation-sql"><code>{item.sparkSql}</code></pre>
      </section>

      <section className="recommendation-snapshot sink-snapshot">
        <div className="recommendation-snapshot-head"><span>03</span><h3>Sink snapshot</h3></div>
        <div><code>{sinkName}</code><span>{item.sink.writeMode}</span></div>
      </section>

      <footer className="recommendation-modal-actions">
        <p>Only Source Data will be copied. Your requirement and Sink stay unchanged.</p>
        <div>
          <button className="secondary-button" onClick={onClose}>Cancel</button>
          <button className="primary-button" disabled={!resolved.selected.length} onClick={apply}>Use Sources</button>
        </div>
      </footer>
    </div>
  </div>
}

export function KnowledgeRecommendations({query, items, availableTables, onUseSources}: KnowledgeRecommendationProps) {
  const [openItem, setOpenItem] = useState<ScoredRecommendation | null>(null)

  return <div className="knowledge-recommendations">
    <div className="knowledge-heading">
      <div><b>Similar Knowledge &amp; Jobs</b><small>Mock knowledge base · ranked from your requirement</small></div>
      {items.length > 0 && <span>{items.length} matches</span>}
    </div>

    {!query.trim()
      ? <div className="knowledge-empty">Describe the transformation to discover similar online jobs and history.</div>
      : <div className="recommendation-grid">
        {items.map(item => <button
          className="recommendation-card"
          key={item.id}
          onClick={() => setOpenItem(item)}
          aria-label={`Open ${item.title} recommendation`}
        >
          <div className="recommendation-card-top">
            <span className={`recommendation-kind ${item.kind}`}>{kindLabel(item.kind)}</span>
            <strong>{item.similarity}%</strong>
          </div>
          <b>{item.title}</b>
          <p>{item.requirement}</p>
          <div className="recommendation-card-meta">
            <span>{item.sources.length} sources</span>
            <span>{item.schedule ?? item.lastUsed ?? 'Snapshot available'}</span>
          </div>
        </button>)}
      </div>}

    {openItem && <RecommendationModal
      item={openItem}
      availableTables={availableTables}
      onClose={() => setOpenItem(null)}
      onUseSources={onUseSources}
    />}
  </div>
}

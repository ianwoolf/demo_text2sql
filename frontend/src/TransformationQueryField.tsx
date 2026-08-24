import {DEMO_QUERY} from './knowledgeRecommendations'

type Props = {
  value: string
  onChange: (value: string) => void
}

export function TransformationQueryField({value, onChange}: Props) {
  return (
    <div className="field transformation-query-field">
      <span className="query-label-row">
        <label htmlFor="transformation-query">What would you like to query?</label>
        <span className="query-example">
          <span>Example: {DEMO_QUERY}</span>
          <button type="button" onClick={() => onChange(DEMO_QUERY)}>Use example</button>
        </span>
      </span>
      <textarea
        id="transformation-query"
        rows={4}
        value={value}
        onChange={event => onChange(event.target.value)}
        placeholder={DEMO_QUERY}
      />
    </div>
  )
}

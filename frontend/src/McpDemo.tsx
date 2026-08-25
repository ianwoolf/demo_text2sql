export type McpDemoScenario = {
  id: string
  title: string
  description: string
  category: 'Analytics' | 'Data Engineering' | 'Operations'
  mcpCount: number
  tools: string[]
  prompt: string
  mode: 'ask' | 'history'
}

export const MCP_DEMO_SCENARIOS: McpDemoScenario[] = [
  {id: 'monthly-sales', title: 'Analyze monthly sales trend', description: 'Query governed sales data and create a chart.', category: 'Analytics', mcpCount: 4, tools: ['Metadata', 'Text2SQL', 'MySQL', 'Visualization'], prompt: 'Show monthly sales this year', mode: 'ask'},
  {id: 'customer-value', title: 'Compare customer value by region', description: 'Apply semantic definitions before querying.', category: 'Analytics', mcpCount: 4, tools: ['Metadata', 'Semantic Layer', 'Text2SQL', 'MySQL'], prompt: 'Compare customer value by region', mode: 'ask'},
  {id: 'build-monthly-sales', title: 'Build a monthly sales dataset', description: 'Turn a request into a governed scheduled pipeline.', category: 'Data Engineering', mcpCount: 5, tools: ['Knowledge Base', 'Metadata', 'Text2SQL', 'SparkJobRunner', 'Airflow'], prompt: 'Build a monthly sales dataset and schedule it daily', mode: 'history'},
  {id: 'backfill', title: 'Backfill the last 90 days', description: 'Prepare and submit a bounded Spark backfill.', category: 'Data Engineering', mcpCount: 3, tools: ['Metadata', 'SparkJobRunner', 'Airflow'], prompt: 'Backfill the monthly sales pipeline for the last 90 days', mode: 'ask'},
  {id: 'investigate-pipeline', title: 'Investigate a failed pipeline', description: 'Correlate DAG state, logs, and source metadata.', category: 'Operations', mcpCount: 3, tools: ['Airflow', 'Logs', 'Metadata'], prompt: 'Investigate why the monthly sales pipeline failed', mode: 'ask'},
  {id: 'schedule-aggregation', title: 'Schedule a daily aggregation', description: 'Create a Spark job and manage its DAG schedule.', category: 'Operations', mcpCount: 4, tools: ['Metadata', 'Text2SQL', 'SparkJobRunner', 'Airflow'], prompt: 'Schedule the regional sales aggregation every day', mode: 'ask'},
]

export function DemoScenarioGrid({onSelect}: {onSelect: (scenario: McpDemoScenario) => void}) {
  return (
    <div className="mcp-scenario-grid">
      {MCP_DEMO_SCENARIOS.map(scenario => (
        <button
          key={scenario.id}
          aria-label={`${scenario.title}, ${scenario.mcpCount} MCPs`}
          onClick={() => onSelect(scenario)}
        >
          <div className="mcp-scenario-top">
            <span className={`scenario-category ${scenario.category.toLowerCase().replace(' ', '-')}`}>{scenario.category}</span>
            <b>{scenario.mcpCount} MCPs</b>
          </div>
          <h3>{scenario.title}</h3>
          <p>{scenario.description}</p>
          <div className="scenario-tools">{scenario.tools.map(tool => <span key={tool}>{tool}</span>)}</div>
        </button>
      ))}
    </div>
  )
}

const SPARK_SQL = `SELECT date_format(o.order_date, 'yyyy-MM') AS month,
       c.region,
       SUM(o.amount) AS completed_sales,
       COUNT(DISTINCT o.customer_id) AS distinct_customers
FROM demo_sales.orders o
JOIN demo_sales.customers c ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
GROUP BY date_format(o.order_date, 'yyyy-MM'), c.region`

type McpStep = {name: string; action: string; duration: string; content: React.ReactNode; status: string}

function McpCall({step}: {step: McpStep}) {
  return (
    <li data-mcp={step.name}>
      <section>
        <header><div><span className="mcp-name">{step.name}</span><h3>{step.action}</h3></div><div className="mcp-step-state"><b>{step.status}</b><small>{step.duration}</small></div></header>
        {step.content}
      </section>
    </li>
  )
}

function UserTurn({children}: {children: React.ReactNode}) {
  return <div className="user-message mcp-user-turn" role="group" aria-label="User message">{children}</div>
}

function ChatbotTurn({title, intro, calls, question, final}: {title: string; intro: string; calls: McpStep[]; question?: string; final?: boolean}) {
  return (
    <article className={`mcp-orchestration-card mcp-chatbot-turn${final ? ' final' : ''}`} aria-label={`Chatbot response: ${title}`}>
      <header><div><span className="mcp-orchestrator-badge">DATACHAT · MCP ORCHESTRATOR</span><h2>{title}</h2></div><span>{calls.length} MCP {calls.length === 1 ? 'call' : 'calls'}</span></header>
      <p className="mcp-intro">{intro}</p>
      <ol className="mcp-timeline mcp-turn-calls" aria-label={`${title} MCP calls`}>
        {calls.map((step, index) => <McpCall key={`${step.name}-${index}`} step={step} />)}
      </ol>
      {question && <div className="mcp-confirmation"><span>CONFIRMATION REQUIRED</span><b>{question}</b><p>I will wait for your confirmation before continuing to the next MCP action.</p></div>}
      {final && <footer className="mcp-summary"><div><b>Goal completed</b><p>The governed dataset, Spark job, and daily Airflow schedule are active.</p></div><span>Next run · tomorrow at 02:00 UTC</span></footer>}
    </article>
  )
}

export function McpHistoryConversation() {
  const discovery: McpStep[] = [
    {name: 'Knowledge Base MCP', action: 'Find reusable jobs and historical operations', duration: '184 ms', status: 'Completed', content: <div className="mcp-result-grid"><span><small>Online job</small><b>Monthly regional sales</b><em>98% match</em></span><span><small>History</small><b>Regional aggregation backfill</b><em>86% match</em></span></div>},
    {name: 'Metadata MCP', action: 'Recommend governed source datasets', duration: '96 ms', status: 'Completed', content: <div className="mcp-source-result"><span><b>demo_sales.orders</b><small>Primary · T1 · Sales Operations</small></span><span><b>demo_sales.customers</b><small>Auxiliary · T2 · CRM Team</small></span></div>},
  ]
  const generation: McpStep[] = [
    {name: 'Text2SQL MCP', action: 'Generate and validate Spark SQL', duration: '2.8 s', status: 'Validated', content: <><pre className="mcp-sql"><code>{SPARK_SQL}</code></pre><p className="mcp-note">Uses the governed customer relationship, filters completed orders, and preserves the month sink partition.</p></>},
    {name: 'Query Engine MCP', action: 'Preview the output dataset', duration: '641 ms', status: 'Succeeded', content: <div className="mcp-preview"><div><b>2026-05</b><span>North</span><strong>1,218,000</strong><em>4,902 customers</em></div><div><b>2026-06</b><span>North</span><strong>1,284,000</strong><em>5,114 customers</em></div></div>},
  ]
  const jobDraft: McpStep[] = [
    {name: 'SparkJobRunner MCP', action: 'Create a submit-ready Spark job', duration: '128 ms', status: 'Waiting for approval', content: <div className="mcp-object"><span><small>Request</small><b>spark_req_0248</b></span><span><small>Sink</small><b>analytics.sales.monthly_region_sales</b></span><span><small>State</small><b>Waiting for approval</b></span></div>},
  ]
  const activation: McpStep[] = [
    {name: 'SparkJobRunner MCP', action: 'Submit the approved Spark job', duration: '326 ms', status: 'Submitted', content: <div className="mcp-object"><span><small>Job</small><b>spark_job_0248</b></span><span><small>Sink</small><b>analytics.sales.monthly_region_sales</b></span><span><small>State</small><b>Ready</b></span></div>},
    {name: 'Airflow MCP', action: 'Create and activate the daily DAG', duration: '212 ms', status: 'Active', content: <div className="mcp-object"><span><small>DAG</small><b>sales_monthly_pipeline</b></span><span><small>Schedule</small><b>0 2 * * *</b></span><span><small>Owner</small><b>Data Platform</b></span><span><small>State</small><b>Active</b></span></div>},
  ]

  return (
    <div className="mcp-history-conversation">
      <UserTurn>Create a monthly regional sales dataset from governed sources and schedule it daily.</UserTurn>
      <ChatbotTurn title="I found a reusable pattern and recommended sources" intro="I checked related production jobs and governed metadata before proposing the source data." calls={discovery} question="Please confirm these business and delivery settings." />

      <UserTurn>Confirmed: completed orders only, grouped by month and region. Use analytics.sales.monthly_region_sales and run daily at 02:00 UTC.</UserTurn>
      <ChatbotTurn title="Spark SQL and output preview are ready" intro="The SQL passed metadata and syntax validation. I also ran a small preview against the selected sources." calls={generation} question="Approve this SQL and preview?" />

      <UserTurn>The SQL and preview look correct. Create the Spark job.</UserTurn>
      <ChatbotTurn title="Spark job request created" intro="The request is packaged with its sources, Spark SQL, sink, and validation evidence." calls={jobDraft} question="Approve the job and activate the daily schedule?" />

      <UserTurn>Approve the job and activate the daily schedule.</UserTurn>
      <ChatbotTurn title="Pipeline activated" intro="Approval received. I submitted the Spark job and activated its Airflow DAG." calls={activation} final />
    </div>
  )
}

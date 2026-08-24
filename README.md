# DataChat POC

An English-only conversational analytics and data-transformation proof of
concept inspired by Waii and Databricks Genie. It combines business data chat,
technical semantic configuration, a multi-source Spark SQL builder, and a task
center for Source / SparkSQL / Sink requests.

## Capabilities

- Natural-language data chat with always-visible Dataset, SQL, execution, and visualization stages.
- Local YAML/JSON metadata provider with a reserved Collibra provider boundary.
- Mock and MySQL query executors; Spark SQL and Hive query targets are reserved.
- Multi-source transformation builder with exactly one primary source.
- Mock or OpenAI-compatible Spark SQL generation and lightweight validation.
- Sink catalog, database, table, write mode, and partition configuration.
- Versioned transformation request snapshots and a Task Center.
- Waiting to Submit, Waiting for Approval, Success, and Failed lifecycle states.
- A reserved `SparkJobRunner` protocol with visibly labeled Demo lifecycle actions.

## Quick Start

Requirements: Python 3.11+ and Node.js 20+.

```bash
# backend: create and activate a virtual environment, then install
cd backend
python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install -e .

cd ../frontend
npm install

cd ..
bash scripts/dev.sh
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Demo mode requires no
database or model credentials.

## Stakeholder Demo

1. Open **Data Chat** and ask “Show monthly sales this year”.
2. Review the visible Dataset, SQL, execution, result table, and visualization.
3. Open **Data Transformation**.
4. Enter a transformation requirement and review the mocked similar jobs and history.
5. Open a recommendation to inspect its Source, SparkSQL, and Sink snapshot; **Use Sources** copies only its Source selection.
6. Confirm the selected Source Data and generate Spark SQL.
7. Configure `analytics.sales.monthly_region_sales` as the Sink.
8. Create the request and open **Task Center**.
9. Submit the request, Demo Approve it, and Demo Mark Success.

## Live Services

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-4.1-mini
export MYSQL_DSN=mysql://readonly:password@127.0.0.1:3306/analytics
```

MySQL must use a database account with read-only permissions. Application SQL
validation does not replace database authorization.

### Anthropic SparkSQL

Data Transformation supports a session-local **Mock / Real LLM** mode. Real LLM uses the native Anthropic Messages API and sends only selected source metadata, the user requirement, known relations, and Sink constraints.

```bash
export ANTHROPIC_API_KEY=...
export ANTHROPIC_BASE_URL=https://api.anthropic.com
export ANTHROPIC_MODEL=...
export ANTHROPIC_TIMEOUT_SECONDS=60
export LOG_LLM_PAYLOADS=true
```

The key remains backend-only. Real LLM never silently falls back to Mock. Invalid SparkSQL is displayed with validation details but cannot create a task. There is no automatic retry or repair; generation runs again only after an explicit user action.

`LOG_LLM_PAYLOADS=true` logs the selected metadata, transformation requirement, Sink constraints, raw model text, token usage, generated SQL, and sqlglot validation result. It never logs the Anthropic API key or authorization headers. Set it to `false` outside local debugging when payload logging is not appropriate.

## SparkSQL Transformation Workflow

The UI is ordered as Requirement → Source Data → SparkSQL → Sink. After the requirement is entered, a frontend mock knowledge base recommends similar online jobs and historical requests. A recommendation can be inspected in full, but applying it copies only its Source selection and clears stale generated SQL; the current requirement and Sink remain unchanged.

The Data Transformation workflow packages selected Source Dataset metadata, generated SparkSQL, and the Sink definition into an immutable request snapshot. The request stops at the `SparkJobRunner` boundary until a real runner integration is provided.

```mermaid
flowchart TD
    A["Select one or more Source Datasets"] --> B["Designate exactly one Primary Source"]
    B --> C["Load selected metadata through Metadata Provider"]
    C --> D["Metadata Preflight"]
    D -->|"Invalid source or metadata"| E["Display detailed errors"]
    D -->|"Valid"| F{"Generation Mode"}

    F -->|"Mock"| G["Generate deterministic demo SparkSQL"]
    F -->|"Real LLM"| H["Build Anthropic prompt"]
    H --> I["Selected metadata + User requirement + Sink constraints"]
    I --> J["Anthropic Messages API"]
    J --> K{"Source context sufficient?"}
    K -->|"No"| L["Display missing information and assumptions"]
    K -->|"Yes"| M["Return structured response and SparkSQL"]

    G --> N["sqlglot Spark AST validation"]
    M --> N
    N -->|"Failed"| O["Display SQL and validation errors"]
    O --> P["User explicitly generates again"]
    P --> F
    N -->|"Passed"| Q["Display editable SQL and LLM details"]
    Q --> R["Create Source / SparkSQL / Sink snapshot"]
    R --> S["Waiting to Submit"]
    S -->|"Submit"| T["Waiting for Approval"]
    T -->|"Approve"| U["Waiting for SparkJobRunner"]
    T -->|"Reject"| V["Failed"]
    U -->|"Runner succeeds"| W["Success"]
    U -->|"Runner fails"| V
```

### 1. Source Dataset metadata

The user can select multiple Source Datasets but must designate exactly one Primary Source. Metadata is loaded through the configured Metadata Provider. The POC currently implements the local YAML provider and reserves the provider interface for Collibra.

Only selected datasets are included in the generation context. Each selected dataset can provide:

- catalog and schema;
- table name and description;
- owner;
- data tier: `T1` raw data, `T2` cleaned data, or `T3` aggregated data;
- selected column names, database data types, nullability, keys, and descriptions; and
- known relationships between selected tables.

Before any LLM call, the backend validates:

- at least one Source Dataset is selected;
- exactly one Source is Primary;
- Dataset IDs are unique and exist in metadata;
- selected columns exist in their Dataset;
- the user requirement is not empty;
- the Sink is not also a Source; and
- Anthropic is configured when Real LLM mode is selected.

Missing known relationships between multiple selected datasets is returned as a warning rather than an immediate error.

### 2. Mock or Anthropic generation

The page-level mode switch is stored in the current browser session and is included in every generation request.

| Mode | Behavior |
|---|---|
| Mock | Returns deterministic demonstration SparkSQL without calling an external model. |
| Real LLM | Calls the native Anthropic Messages API. It never silently falls back to Mock. |

Real LLM generation uses all three inputs:

1. selected Source Dataset metadata;
2. the user's transformation requirement; and
3. the Sink name and partition constraints.

Anthropic must return structured JSON containing context sufficiency, missing information, assumptions, SparkSQL, referenced tables, output columns, and an explanation. The backend retains sanitized model text for the expandable `View Raw LLM Response` section. API keys, authorization headers, SDK objects, and stack traces are never returned to the browser.

### 3. sqlglot SparkSQL review

The backend does not trust the model's declared tables or output columns. It parses the returned SQL using `sqlglot` with the Spark dialect and independently checks:

- exactly one `SELECT` or `WITH ... SELECT` query;
- absence of DDL, DML, cache, command, and filesystem operations;
- physical tables are limited to selected Sources;
- CTE aliases are distinguished from physical tables;
- referenced columns exist in selected metadata;
- qualified aliases resolve to the correct Source;
- output column names are present and unique; and
- every Sink partition column is present in the final output.

Validation returns referenced tables, output columns, known joins, warnings, and errors. Failed SQL is shown for inspection but cannot be packaged into a transformation request.

The backend does not automatically retry or repair failed SQL. A new Anthropic call occurs only after an explicit user generation action. When available, the previous SQL and validation errors are included as context for that user-triggered request.

### 4. LLM result presentation

The page keeps the generation result visible and presents:

- editable generated SparkSQL;
- model explanation;
- Source sufficiency;
- missing information and assumptions;
- backend validation errors and warnings;
- model name, latency, and token usage; and
- the collapsed sanitized Raw LLM Response.

Changing a Source, Primary Source, transformation requirement, or Sink partition invalidates the previous result. A valid generated SQL artifact is required before creating a request.

### 5. Request snapshot and approval

Creating a transformation request stores Source, SparkSQL, validation, and Sink as one versioned snapshot. The lifecycle is:

| Status | Meaning |
|---|---|
| `waiting_submit` | The request is saved and can still be reviewed before submission. |
| `waiting_approval` | The request was submitted and is waiting for approval. |
| `success` | The future Spark runner completed successfully. |
| `failed` | Approval was rejected or execution failed. |

After approval, the POC stops at `runner_not_configured`. `SparkJobRunner` is an interface placeholder: the current Demo controls can simulate success or failure, but no real Spark job is submitted.

## Verification

```bash
cd backend && APP_DATABASE_PATH=/tmp/datachat-test.db python3 -m pytest -q
cd frontend && npm run build
bash -n scripts/dev.sh
```

## POC Limits

- The UI role switch is not authentication.
- Spark jobs are not submitted; `SparkJobRunner` is an interface only.
- Task approval and success/failure controls are Demo simulations.
- Collibra, Spark SQL, and Hive integrations are reserved but not connected.
- There is no scheduling, job logging, real field-level lineage, SSO, or multi-tenancy.

Design and implementation records are under `docs/superpowers/`.

<div align="center">

# FinOps for Agents

**Know exactly who is spending what on your AI agents — down to the token.**

A reference implementation that captures per-user, per-agent token consumption from
Microsoft Foundry agents, converts it into [FOCUS™ 1.0](https://focus.finops.org/)-compliant
cost records, and streams it to Azure Log Analytics for reporting, chargeback and alerting —
then reads it back out over a [REST API](#the-rest-api) and
[MCP](#ask-your-data-in-natural-language), so you can ask "who spent the most on this agent
last month?" from a script or in plain English.

[Why](#why-this-exists) · [How it works](#architecture) · [Quickstart](#quickstart) · [Queries](#querying-your-data) · [REST](#the-rest-api) · [MCP](#ask-your-data-in-natural-language) · [Limits](#known-limitations) · [Roadmap](#roadmap)

</div>

---

![Token Consumption by Department](./images/tokens_by_department.png)

<sub>*Live token consumption per department for a single Foundry agent. Every bar is real usage attributed back to a cost centre — the basis for showback, chargeback and optimisation.*</sub>

---

## Why this exists

Organisations are deploying AI agents fast. Their finance teams cannot keep up.

Unlike compute or storage, **AI agent cost is consumption-driven**: every token processed by
every user carries a price. But the bill that arrives at the end of the month is a single
number per model deployment. There is no answer to the questions that actually matter:

| Question | Can you answer it today? |
|---|---|
| Which department is driving 40% of our agent spend? | ❌ |
| Is this agent worth the money it costs to run? | ❌ |
| Which users are burning tokens on inefficient prompts? | ❌ |
| What should we budget for AI next quarter? | ❌ |
| Can we charge these costs back to the business units using them? | ❌ |

The result is a familiar pattern: **strong adoption, weak financial control.** Teams either
over-provision and waste money, or freeze adoption because nobody can defend the spend.

### What this project changes

`FinOps for Agents` closes the attribution gap at the point of consumption. It sits between
the user and the agent, enriches every request with organisational identity, captures the exact
token usage the model reports back, and writes a standards-compliant cost record.

- **Attribution at source** — identity is captured from Teams and enriched via Microsoft Graph
  (department, cost centre, job title), not reconstructed after the fact.
- **FOCUS 1.0 compliant** — records use the FinOps Foundation's open billing schema, so they
  drop into existing FinOps tooling instead of becoming another silo.
- **Provider-agnostic data model** — the schema describes *agent* cost, not *Foundry* cost.
  Swap the agent runtime; the pipeline and dashboards keep working.
- **Actionable, not just observable** — ships with KQL queries, an importable Azure Workbook,
  and anomaly-based alert rules for runaway consumption.
- **Queryable however you ask** — a REST endpoint on the bot service for scripts and
  dashboards, and an MCP server that puts the same cost data directly in front of
  Claude, Copilot or any MCP client, so answering a chargeback question does not require
  knowing KQL.

### Business outcomes

| Capability | Outcome |
|---|---|
| **Showback & chargeback** | Allocate agent cost to the departments that generate it |
| **Optimisation** | Identify the top 5% of users driving disproportionate token spend |
| **Budgeting** | Forecast from actual consumption trends instead of estimates |
| **Governance** | Alert on anomalous spend before it appears on an invoice |

---

## Architecture

### Data flow

```mermaid
graph LR
    A["👤 Microsoft Teams<br/><i>user sends a message</i>"]
    B["🤖 Bot Service<br/><i>Flask middleware</i>"]
    C["🪪 Microsoft Graph<br/><i>department, title, office</i>"]
    D["🧠 Foundry Agent<br/><i>gpt-5-mini</i>"]
    E["📐 FinOps Record<br/><i>FOCUS 1.0</i>"]
    F["🗄️ Log Analytics<br/><i>FinOpsAgentMetrics_CL</i>"]
    G["📊 Workbook / Power BI"]
    H["🚨 Alert Rules"]
    I["🔎 KQL / Ad-hoc"]
    J["🧩 MCP Server<br/><i>Azure Functions</i>"]
    K["💬 AI Assistant<br/><i>Claude, Copilot, …</i>"]
    L["🌐 REST API<br/><i>departments · billing</i>"]

    A --> B
    B -->|enrich identity| C
    B -->|forward prompt| D
    C -->|user attributes| E
    D -->|tokens, model, timing| E
    E -->|HTTPS + HMAC| F
    F --> G
    F --> H
    F --> I
    F -->|KQL over Entra ID| J
    F -->|KQL over Entra ID| L
    J -->|MCP tools| K

    style A fill:#e0e7ff,stroke:#4338ca
    style B fill:#fef3c7,stroke:#b45309
    style C fill:#fef3c7,stroke:#b45309
    style D fill:#d1fae5,stroke:#047857
    style E fill:#f3e8ff,stroke:#7e22ce
    style F fill:#dbeafe,stroke:#1d4ed8
    style G fill:#dbeafe,stroke:#1d4ed8
    style H fill:#dbeafe,stroke:#1d4ed8
    style I fill:#dbeafe,stroke:#1d4ed8
    style J fill:#dbeafe,stroke:#1d4ed8
    style K fill:#e0e7ff,stroke:#4338ca
    style L fill:#dbeafe,stroke:#1d4ed8
```

The left half of the diagram is the **write path** — every Teams message produces one priced,
validated cost record. The right half is the **read path**: dashboards and alerts for
scheduled consumption, a REST endpoint for scripts and dashboards, and the MCP server for
ad-hoc questions. The REST API is served by the same Flask app as the bot, on the same port.

> A higher-detail diagram is available at [`images/architecture-diagram.svg`](./images/architecture-diagram.svg).

### Components

| Component | Location | Responsibility |
|---|---|---|
| **Bot Service** | [`code/bot_service.py`](./code/bot_service.py) | Flask app on `:3978`. Receives Bot Framework activities, orchestrates the pipeline, replies to Teams. Also serves the [read endpoints](#the-rest-api) — `/api/departments`, `/api/{agent_name}/billing` — and `/health`. |
| **Auth helpers** | [`code/utils.py`](./code/utils.py) | Client-credentials token acquisition for three distinct scopes: Bot Framework, Graph, and Foundry. Decodes the inbound Teams JWT. |
| **Identity enrichment** | [`code/user_metadata.py`](./code/user_metadata.py) | Extracts the AAD object ID from the activity, then calls Graph `/users/{id}` to resolve department, job title, office and mail. |
| **Agent client** | [`code/foundry_agent.py`](./code/foundry_agent.py) | Calls the Foundry agent over the OpenAI-compatible Responses protocol and parses `usage` (input / output / reasoning tokens), model, agent version and timings. |
| **Pricing** | [`code/pricing.py`](./code/pricing.py) | Resolves real per-token USD rates for the model from the Azure Retail Prices API — input, cached input and output separately — cached in-process. Falls back to static rates if the API is unreachable. |
| **Metrics pipeline** | [`code/finops_metrics.py`](./code/finops_metrics.py) | Builds the FOCUS record, validates it, prices it, and ships it to Log Analytics via the Data Collector API (HMAC-SHA256 signed). |
| **Metrics queries** | [`code/finops_query.py`](./code/finops_query.py) | The read side of the same table. Runs KQL aggregations over `FinOpsAgentMetrics_CL` via `DefaultAzureCredential` and shapes the rows into JSON for the REST endpoints. |
| **Data model** | [`finops_data_layer/`](./finops_data_layer/) | `schema.json` (JSON Schema 2020-12, 55 fields, 22 required) plus a typed Python builder and validator. |
| **Infrastructure** | [`infra/`](./infra/) | Terraform for the resource group, Foundry account + project, `gpt-5-mini` deployment, Log Analytics, Application Insights, Storage, Cosmos DB and AI Search. |
| **Dashboard** | [`dashboards/finops-dashboard.json`](./dashboards/finops-dashboard.json) | Importable Azure Workbook: department, model pricing, and user-to-model usage and cost views. |
| **MCP server** | [`mcp_server/function_app.py`](./mcp_server/function_app.py) | Azure Functions app exposing the cost data as MCP tools, so an AI assistant can answer chargeback questions without writing KQL. Reads via `DefaultAzureCredential`. |
| **Teams app** | [`teams_app/`](./teams_app/) | Manifest and icons for sideloading the bot into Teams. |

### The data model

Every interaction produces one record conforming to
[`finops_data_layer/schema.json`](./finops_data_layer/schema.json). It uses standard FOCUS
columns where they exist and the FOCUS-sanctioned `x_` prefix for agent-specific extensions:

| Group | Fields |
|---|---|
| **Billing (FOCUS)** | `BillingAccountId`, `BillingPeriodStart/End`, `BillingCurrency`, `ChargePeriodStart/End` |
| **Service (FOCUS)** | `ServiceCategory`, `ServiceName`, `ServiceSubcategory`, `SkuId`, `SkuMeterName` |
| **Resource (FOCUS)** | `ResourceId`, `ResourceName`, `ResourceType`, `RegionId`, `RegionName` |
| **Cost (FOCUS)** | `EffectiveCost`, `BilledCost`, `ListCost`, `ConsumedQuantity`, `ConsumedUnit` |
| **Identity (`x_`)** | `x_UserId`, `x_UserEmail`, `x_UserName`, `x_UserDepartment`, `x_CostCenter`, `x_TeamId` |
| **Agent (`x_`)** | `x_AgentId`, `x_AgentName`, `x_AgentVersion`, `x_ModelId`, `x_ModelName`, `x_ModelFamily` |
| **Pricing (`x_`)** | `x_InputPricePerMillionTokens`, `x_CachedInputPricePerMillionTokens`, `x_OutputPricePerMillionTokens` |
| **Tokens (`x_`)** | `x_InputTokens`, `x_CachedInputTokens`, `x_OutputTokens`, `x_ReasoningTokens`, `x_TotalTokens`, `x_TokensPerSecond` |
| **Execution (`x_`)** | `x_CreatedAt`, `x_CompletedAt`, `x_ProcessingTimeSeconds`, `x_RequestId`, `x_Channel` |

Records are validated against the schema **before** they are shipped — a malformed record is
logged and dropped rather than silently corrupting the dataset.

### What actually lands in Log Analytics

> **The FOCUS record and the Log Analytics table are not the same shape.** The record has 55
> fields; the ingestion payload in
> [`code/finops_metrics.py`](./code/finops_metrics.py) projects a subset of them. Query the
> columns below — the other FOCUS fields exist in the record but never reach the workspace.

`FinOpsAgentMetrics_CL` has these columns (plus the standard `TimeGenerated`, `Type`,
`TenantId` and `_ResourceId` that Log Analytics adds to every custom table):

| Column | Type | From |
|---|---|---|
| `TimeGenerated` | `datetime` | Ingestion timestamp — use this for every time filter |
| `UserEmail_s` | `string` | `x_UserEmail` |
| `UserDepartment_s` | `string` | `x_UserDepartment` — see [Known limitations](#known-limitations) |
| `AgentName_s` | `string` | `x_AgentName` |
| `AgentVersion_s` | `string` | `x_AgentVersion` |
| `ModelId_s` | `string` | `x_ModelId` |
| `RequestId_s` | `string` | `x_RequestId` |
| `InputTokens_d` | `real` | `x_InputTokens` |
| `OutputTokens_d` | `real` | `x_OutputTokens` |
| `TotalTokens_d` | `real` | `x_TotalTokens` |
| `EffectiveCost_d` | `real` | `EffectiveCost` |
| `ProcessingTimeSeconds_d` | `real` | `x_ProcessingTimeSeconds` |

**Why the `_s` and `_d` suffixes?** The legacy HTTP Data Collector API infers a type from each
JSON value and appends a suffix to the column name: `_s` string, `_d` double, `_b` boolean,
`_t` datetime, `_g` GUID. You do not choose these names — they are generated. Two consequences
worth knowing:

- **There is no integer suffix.** Token counts are stored as `real`, which is why sums can come
  back as `0.30124999999999996` rather than `0.30125`. Round at the presentation layer.
- **`Timestamp` does not survive.** The payload sends it and declares it as the
  `time-generated-field`, so it is folded into `TimeGenerated` rather than becoming a
  `Timestamp_t` column. Filter on `TimeGenerated`.

Migrating to the [Logs Ingestion API with a DCR](https://learn.microsoft.com/azure/azure-monitor/logs/logs-ingestion-api-overview)
would let you declare column names and types explicitly and drop the suffixes entirely — see
the [Roadmap](#roadmap).

---

## Quickstart

### Prerequisites

- **Azure subscription** with permission to create Cognitive Services, Log Analytics and Cosmos DB
- **Terraform** ≥ 1.5 and **Azure CLI**, authenticated (`az login`)
- **Python** 3.11+
- **Microsoft Teams** with permission to sideload a custom app
- **DevTunnel** or ngrok, to expose your local bot to the Bot Service
- An **Azure AD app registration** for the bot with the Graph *Application* permissions
  `User.Read.All` and `Directory.Read.All` (admin consent granted)
- The **Log Analytics Reader** role on the workspace, for the identity you are signed in as —
  required by both the [REST API](#the-rest-api) and the
  [MCP server](#ask-your-data-in-natural-language), which read over Entra ID rather than the
  shared key
- *Optional, for the MCP server:* **Azure Functions Core Tools v4** (`func`)

### 1. Deploy the infrastructure

```bash
cd infra
cp example.tfvars terraform.tfvars     # then edit: set `location` and `bot_app_id`

terraform init
terraform plan  -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

This provisions the Foundry account and project, a `gpt-5-mini` deployment, the Log Analytics
workspace (`log-analytics-finops-for-agents`, 90-day retention) and Application Insights wired
into it. Note the outputs — you need them in step 3:

```bash
terraform output foundry_account_url
terraform output foundry_project_name
terraform output log_analytics_workspace_name
```

### 2. Create your agent in Foundry

In the [Microsoft Foundry portal](https://ai.azure.com), open the project created above and
create an agent on the `gpt-5-mini` deployment. Give the bot's service principal the
**Foundry Agent Consumer** role on the project, or calls will fail with `403`.

### 3. Configure the bot

```bash
cd code
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

> **Do not downgrade `botbuilder-core` / `botbuilder-schema` below 4.17.1.** Version 4.14.2
> hard-pins `msal==1.6.0`, which cannot coexist with `azure-identity` (`msal>=1.30.0`) — the
> install fails with `ResolutionImpossible`. 4.17.1 relaxes the pin to `msal>=1.31.1`.

Create `code/.env` (git-ignored):

```dotenv
BOT_APP_ID=<bot app registration client id>
BOT_APP_PASSWORD=<bot app registration client secret>
BILLING_ACCOUNT_ID=<azure subscription id>
APPLICATIONINSIGHTS_INSTRUMENTATION_KEY=<from terraform output>
LOG_ANALYTICS_SHARED_KEY=<workspace primary key>

# Optional — token pricing lookup (defaults shown)
PRICING_REGION=swedencentral
PRICING_CACHE_TTL_SECONDS=86400
```

Retrieve the Log Analytics workspace key with:

```bash
az monitor log-analytics workspace get-shared-keys \
  --resource-group ms-hackathon-finops-agent-rg \
  --workspace-name log-analytics-finops-for-agents
```

> **Also set the Foundry endpoint.** `FOUNDRY_ENDPOINT` at the top of
> [`code/foundry_agent.py`](./code/foundry_agent.py) and `LOG_ANALYTICS_WORKSPACE_ID` in
> [`code/finops_metrics.py`](./code/finops_metrics.py) currently hold the demo deployment's
> values. Point them at your own project and workspace.
> [`code/finops_query.py`](./code/finops_query.py) reads the same workspace GUID from a
> `LOG_ANALYTICS_WORKSPACE_ID` environment variable, falling back to the demo value — add it to
> `.env` alongside the keys above.

### 4. Run it

```bash
python bot_service.py          # listens on http://0.0.0.0:3978
```

In a second terminal, expose the service and copy the public HTTPS URL:

```bash
devtunnel host -a -p 3978
```

Set the Bot Service **messaging endpoint** to `https://<your-tunnel>/api/messages` in the
Azure portal (Bot → Configuration).

### 5. Talk to it from Teams

Sideload [`teams_app/`](./teams_app/) (zip the manifest with both icons) or open the bot
directly from the Bot Service *Channels → Teams* blade. Send a message. The bot replies with
the resolved user profile and the token accounting for that turn.

Console output confirms the record was shipped:

```
[PRICING] Fetching prices for 'gpt-5-mini' in swedencentral from https://prices.azure.com/api/retail/prices
[PRICING]   HTTP 200 in 547 ms
[PRICING]   3 of 3 expected meter(s) returned
[PRICING]   input        'GPT 5 Mini Inpt Glbl 1M Tokens' = $0.25 per 1M -> $0.000000250/token
[PRICING]   cached_input 'GPT 5 Mini cchd Inpt Glbl 1M Tokens' = $0.025 per 1M -> $0.000000025/token
[PRICING]   output       'GPT 5 Mini outpt Glbl 1M Tokens' = $2.0 per 1M -> $0.000002000/token
[PRICING] Cached prices for 'gpt-5-mini' for the next 24h
[FINOPS] ========== FINOPS METRICS RECORDED ==========
[FINOPS] User: alice@contoso.com
[FINOPS] Department: IT Operations
[FINOPS] Agent: super-fun-coding-learn-agent (v1)
[FINOPS] Input Tokens: 4,342 (cached: 3,968)
[FINOPS] Output Tokens: 731 (reasoning: 128)
[FINOPS] Total Tokens: 5,073
[FINOPS] Cost: $0.0016
[APPINSIGHTS] ✅ Sent FinOps record to Log Analytics
```

The `[PRICING]` block appears once per model per 24 hours — subsequent requests are served
from the in-process cache and log nothing. If a meter is missing or the API is unreachable,
the failure is logged and static fallback rates are used instead.

> **First ingestion takes 2–5 minutes.** Log Analytics creates the `FinOpsAgentMetrics_CL`
> table on the first successful POST; queries return empty until then.

### 6. Verify

```bash
curl http://localhost:3978/health          # {"status":"healthy"}
```

Then in the Log Analytics workspace:

```kql
FinOpsAgentMetrics_CL
| take 10
```

Or read the same data straight back out of the bot service — `az login` first, since this path
authenticates over Entra ID rather than the shared key:

```bash
curl -s http://localhost:3978/api/departments | jq '.totals'
curl -s "http://localhost:3978/api/super-fun-coding-learn-agent/billing?department=HR" | jq '.billed_cost'
```

See [The REST API](#the-rest-api) for parameters and the full response shapes.

---

## Querying your data

### Token consumption by department

The primary chargeback view — this is the query behind the chart at the top of this README:

```kql
FinOpsAgentMetrics_CL
| where AgentName_s == "super-fun-coding-learn-agent"
| summarize TotalTokens = sum(TotalTokens_d) by UserDepartment_s
| sort by TotalTokens desc
```

### Top consuming users

![Top Users Sample](./images/top_3_users_sample.png)

```kql
FinOpsAgentMetrics_CL
| where AgentName_s == "super-fun-coding-learn-agent"
| summarize
    TotalTokens       = sum(TotalTokens_d),
    TotalCost         = sum(EffectiveCost_d),
    RequestCount      = count(),
    AvgCostPerRequest = avg(EffectiveCost_d)
    by UserEmail_s
| top 5 by TotalTokens desc
```

`AvgCostPerRequest` is the efficiency signal: a user with high total cost but low cost per
request is simply a heavy user; a user with high cost *per request* is a prompting problem you
can fix with training.

> Beware the pie chart. `top 5` truncates the result set, so a percentage rendered from it is a
> share of those five — not of the agent. The
> [`query_agent_top_users` MCP tool](#available-tools) issues a second aggregation over all
> users to return an honest `ShareOfAgentTokens`.

### Model prices and usage

Each request records the input, cached-input and output rates used to calculate its cost. The
rates are normalized to USD per one million tokens so models with differently sized Azure
meters remain directly comparable.

```kql
let modelUsage = FinOpsAgentMetrics_CL
| summarize
      TotalTokens = sum(TotalTokens_d),
      TotalCost = sum(EffectiveCost_d),
      RequestCount = count()
      by Model = ModelId_s;
let latestModelPrices = FinOpsAgentMetrics_CL
| extend
      InputPriceUSDPer1M = todouble(column_ifexists("InputPricePerMillionTokens_d", real(null))),
      CachedInputPriceUSDPer1M = todouble(column_ifexists("CachedInputPricePerMillionTokens_d", real(null))),
      OutputPriceUSDPer1M = todouble(column_ifexists("OutputPricePerMillionTokens_d", real(null)))
| where isnotnull(InputPriceUSDPer1M)
| summarize arg_max(TimeGenerated, InputPriceUSDPer1M, CachedInputPriceUSDPer1M, OutputPriceUSDPer1M)
      by Model = ModelId_s
| project Model, InputPriceUSDPer1M, CachedInputPriceUSDPer1M, OutputPriceUSDPer1M;
modelUsage
| join kind=leftouter latestModelPrices on Model
| project Model, InputPriceUSDPer1M, CachedInputPriceUSDPer1M,
      OutputPriceUSDPer1M, TotalTokens, TotalCost, RequestCount
| order by TotalCost desc
```

### Usage by user and model

```kql
FinOpsAgentMetrics_CL
| extend
      CachedInputTokens = todouble(column_ifexists("CachedInputTokens_d", 0.0)),
      InputPriceUSDPer1M = todouble(column_ifexists("InputPricePerMillionTokens_d", real(null))),
      CachedInputPriceUSDPer1M = todouble(column_ifexists("CachedInputPricePerMillionTokens_d", real(null))),
      OutputPriceUSDPer1M = todouble(column_ifexists("OutputPricePerMillionTokens_d", real(null)))
| summarize
      TotalTokens = sum(TotalTokens_d),
      InputTokens = sum(InputTokens_d),
      CachedInputTokens = sum(CachedInputTokens),
      OutputTokens = sum(OutputTokens_d),
      TotalCost = sum(EffectiveCost_d),
      RequestCount = count(),
      arg_max(TimeGenerated, InputPriceUSDPer1M, CachedInputPriceUSDPer1M, OutputPriceUSDPer1M)
      by UserEmail = iff(isempty(UserEmail_s), "N/A", UserEmail_s), Model = ModelId_s
| project UserEmail, Model, InputPriceUSDPer1M, CachedInputPriceUSDPer1M,
      OutputPriceUSDPer1M, InputTokens, CachedInputTokens, OutputTokens,
      TotalTokens, TotalCost, RequestCount
| order by UserEmail asc, TotalCost desc
```

The price columns are populated on newly ingested records. Historical rows remain in each
aggregation but show blank prices. If the Retail Prices API is unavailable, the columns contain
the static fallback rates that were actually used for the cost calculation.

### Anomaly detection

```kql
FinOpsAgentMetrics_CL
| where AgentName_s == "super-fun-coding-learn-agent"
| make-series TotalTokens = sum(TotalTokens_d) on TimeGenerated step 1h by UserDepartment_s
| extend anomalies = series_decompose_anomalies(TotalTokens, 1.5)
| render anomalychart
```

`series_decompose_anomalies` learns each department's baseline and flags deviations. The
sensitivity parameter (`1.5`) is a z-score threshold — lower it to catch more, raise it to
reduce noise.

### Importing the dashboard

Log Analytics → **Workbooks** → **New** → **</> Advanced Editor** → paste the contents of
[`dashboards/finops-dashboard.json`](./dashboards/finops-dashboard.json) → **Apply**.

Update `fallbackResourceIds` in that file to your own workspace resource ID first. The imported
Workbook includes **Model Prices and Usage**, **Token Consumption Grouped by Model**,
**Usage and Cost by User and Model**, and a
**Department to User to Model to Token Consumption Flow** graph.
Workbook JSON contains queries rather than a frozen price list: the three price values appear
after the updated bot ingests at least one request for that model. Existing Workbooks do not
automatically pick up repository changes, so re-import version `1.2.0.0` after updating this file.

---

## The REST API

The department breakdown is also available as plain HTTP GETs on the bot service, so a script,
a web page or a scheduled job can pull it without a workspace connection or a KQL query.

Two endpoints, same rows, different question: `/api/departments` leads with tokens — *who is
using this agent?* — and `/api/{agent_name}/billing` leads with cost — *what does each
department owe?*

Both are served by the same Flask app as the bot, on the same port, and backed by
[`code/finops_query.py`](./code/finops_query.py).

### `GET /api/departments`

Returns every department that used a given agent — token consumption, input/output split,
estimated cost, request count and distinct users — sorted by total tokens descending, plus
agent-wide totals.

| Parameter | Default | Notes |
|---|---|---|
| `agent_name` | `super-fun-coding-learn-agent` | Exact `AgentName_s` value, **case-sensitive**. Restricted to 1–128 characters of letters, digits, spaces, dots, underscores and hyphens: the value is interpolated into the KQL, so anything outside that set is rejected rather than escaped. |
| `days` | `90` | Look-back window, 1–730. The workspace retains 90 days, so larger windows do not return more data. |

```bash
curl -s "http://localhost:3978/api/departments?agent_name=super-fun-coding-learn-agent&days=90" | jq
```

```json
{
  "agent_name": "super-fun-coding-learn-agent",
  "days": 90,
  "department_count": 5,
  "departments": [
    {
      "Department": "N/A",
      "InputTokens": 60761,
      "OutputTokens": 8253,
      "RequestCount": 14,
      "TotalCost": 0.57997105,
      "TotalTokens": 69014,
      "UniqueUsers": 4
    }
  ],
  "table": "FinOpsAgentMetrics_CL",
  "totals": {
    "InputTokens": 169348,
    "OutputTokens": 20605,
    "RequestCount": 38,
    "TotalCost": 1.609469,
    "TotalTokens": 189953
  },
  "workspace_id": "1704fbb7-e360-449c-af0b-ea430a93b9b8"
}
```

*(one department shown; the live response carries all five. Flask serialises keys
alphabetically — `departments` is still sorted by `TotalTokens` descending.)*

| Status | When |
|---|---|
| `200` | Query succeeded. An agent with no records still returns `200`, with `department_count: 0` and an explanatory `note`. |
| `400` | `days` is not a whole number or falls outside 1–730, or `agent_name` failed the character allow-list. |
| `502` | The Log Analytics query itself failed — see `detail`. |

### `GET /api/{agent_name}/billing`

The chargeback view of the same rows: led by cost, with each department's share of the agent's
spend and its average cost per request. Add `?department=` to bill a single department.

The agent name lives in the path here rather than the query string, so a URL reads as the thing
it identifies: `/api/super-fun-coding-learn-agent/billing`.

| Parameter | In | Default | Notes |
|---|---|---|---|
| `agent_name` | path | — | Exact `AgentName_s` value, **case-sensitive**, same allow-list as above. URL-encode spaces as `%20`. |
| `department` | query | *all* | Matched **case-insensitively**, so `hr`, `HR` and `Hr` are the same department. Omit it for every department. |
| `days` | query | `90` | Look-back window, 1–730. |

```bash
curl -s "http://localhost:3978/api/super-fun-coding-learn-agent/billing?department=HR" | jq
```

```json
{
  "agent_name": "super-fun-coding-learn-agent",
  "agent_total_cost": 1.609469,
  "billed_cost": 0.23614,
  "billing": [
    {
      "AvgCostPerRequest": 0.059035,
      "Cost": 0.23614,
      "CostShare": 0.1467,
      "Department": "HR",
      "InputTokens": 17377,
      "OutputTokens": 2079,
      "RequestCount": 4,
      "TotalTokens": 19456,
      "UniqueUsers": 1
    }
  ],
  "cost_basis": "Estimate from the hardcoded rates in finops_metrics.py. Not reconciled against the Azure invoice.",
  "currency": "USD",
  "days": 90,
  "department": "HR",
  "department_count": 1,
  "table": "FinOpsAgentMetrics_CL",
  "workspace_id": "1704fbb7-e360-449c-af0b-ea430a93b9b8"
}
```

`CostShare` is HR's share of the agent's **whole** spend — 14.67% of `agent_total_cost`, not of
`billed_cost`. That is deliberate: the department filter is applied after the aggregation, so a
filtered response still tells you how big that slice is relative to everything the agent spent.
A share of the filtered rows would always be 100% and answer nothing.

`cost_basis` is not decoration. These figures come from the placeholder rates in
`finops_metrics.py`, not from your Azure invoice — see
[Known limitations](#known-limitations) before anyone acts on a number called *billing*.

| Status | When |
|---|---|
| `200` | Query succeeded. An unknown department returns `200` with `department_count: 0` and a `note` listing the departments that *do* have usage. |
| `400` | Same validation as `/api/departments` — bad `days`, or an `agent_name` outside the allow-list. |
| `502` | The Log Analytics query failed — see `detail`. |

A `warning` field appears on either endpoint when Log Analytics returns a partial result; the
rows it did return are still included.

> **Reads use a different credential than writes.** Ingestion signs with
> `LOG_ANALYTICS_SHARED_KEY`, but `api.loganalytics.io` accepts only Entra ID bearer tokens.
> These endpoints therefore authenticate with `DefaultAzureCredential` — `az login` locally, a
> managed identity once hosted — and that identity needs **Log Analytics Reader** on the
> workspace. A `502` mentioning `DefaultAzureCredential failed to retrieve a token` means you
> are not signed in; see [Access and configuration](#access-and-configuration) for the role
> assignment.

### A quick table in the terminal

```bash
curl -s "http://localhost:3978/api/departments" \
  | jq -r '["DEPARTMENT","TOKENS","INPUT","OUTPUT","REQS"],
           (.departments[] | [.Department,.TotalTokens,.InputTokens,.OutputTokens,.RequestCount])
           | @tsv' \
  | column -t -s $'\t'
```

```
DEPARTMENT     TOKENS  INPUT  OUTPUT  REQS
N/A            69014   60761  8253    14
Engineering    39434   34752  4682    7
IT Operations  37532   34745  2787    8
Marketing      24517   21713  2804    5
HR             19456   17377  2079    4
```

Use `-s $'\t'` rather than the default separator — department names contain spaces, and
`column -t` alone will split *IT Operations* across two columns.

The same shape for the billing endpoint, as a chargeback sheet:

```bash
curl -s "http://localhost:3978/api/super-fun-coding-learn-agent/billing" \
  | jq -r '["DEPARTMENT","COST","SHARE","PER-REQ","REQS"],
           (.billing[] | [.Department, .Cost,
                          ((.CostShare*10000|round)/100|tostring)+"%",
                          .AvgCostPerRequest, .RequestCount])
           | @tsv' \
  | column -t -s $'\t'
```

```
DEPARTMENT     COST      SHARE   PER-REQ   REQS
N/A            0.579971  36.03%  0.041427  14
Engineering    0.061048  3.79%   0.008721  7
IT Operations  0.43106   26.78%  0.053882  8
Marketing      0.30125   18.72%  0.06025   5
HR             0.23614   14.67%  0.059035  4
```

The `round` is not cosmetic. `CostShare * 100` on a float gives `3.7900000000000005`, because
the token counts behind it are stored as doubles — the Data Collector API has no integer type.

---

## Ask your data in natural language

KQL and workbooks answer the questions you thought to build a tile for. The MCP server in
[`mcp_server/`](./mcp_server/) covers the rest: it exposes the cost data as
[Model Context Protocol](https://modelcontextprotocol.io) tools, so an assistant can answer
*"which departments used this agent last quarter?"* directly.

It is an Azure Functions app (Python v2 model) using the Functions MCP extension. Each tool
validates its arguments, runs a parameterised KQL query against the workspace via
`DefaultAzureCredential`, and returns JSON.

### Available tools

| Tool | Parameters | Returns |
|---|---|---|
| `query_agent_usage_by_department` | `agent_name` (required), `days` (default 30) | One row per department: total tokens, input/output split, cost, request count, distinct users — sorted by tokens descending, plus agent-wide totals. |
| `query_agent_top_users` | `agent_name` (required), `days` (default 30), `top_n` (default 3, max 50) | The heaviest `top_n` users: tokens, cost, request count, average cost per request, and `ShareOfAgentTokens`. |

`ShareOfAgentTokens` is deliberately computed against **every** user, not just the returned
ones. A naive `top 3` renders a pie chart whose slices add to 100% even when those three
account for a fraction of real spend; the tool issues a second aggregation over the full
population so the share is honest.

### Running it locally

```bash
cd mcp_server
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

func start                     # http://localhost:7071
```

Point your MCP client at the endpoint. For Claude Code:

```bash
claude mcp add --transport http finops http://localhost:7071/runtime/webhooks/mcp
```

The SSE transport is available at `/runtime/webhooks/mcp/sse` if your client requires it.

### Access and configuration

The server reads from Log Analytics with `DefaultAzureCredential`, so whichever identity you
are signed in as needs the **Log Analytics Reader** role on the workspace. The same assignment
covers the [REST API](#the-rest-api), which reads the same way:

```bash
az role assignment create \
  --role "Log Analytics Reader" \
  --assignee <your-upn-or-principal-id> \
  --scope /subscriptions/<sub>/resourceGroups/ms-hackathon-finops-agent-rg/providers/Microsoft.OperationalInsights/workspaces/log-analytics-finops-for-agents
```

Set `LOG_ANALYTICS_WORKSPACE_ID` in `mcp_server/local.settings.json` to your own workspace GUID
— the value in the source is the demo workspace and is only a fallback.

> **Two things that will cost you ten minutes each.**
> Newly added tools are registered at host startup, so after editing `function_app.py` you must
> **restart `func start`** — a running host will not surface a new `@app.mcp_tool`.
> And `host.json` sets `webhookAuthorizationLevel: Anonymous`, which is correct for local
> development and **must not** be deployed as-is; see the [Roadmap](#roadmap).

### A note on multi-statement queries

`query_agent_top_users` returns two result tables from one round trip. The Python
`LogsQueryClient` handles this correctly, but some clients — including the Azure MCP
`monitor` tool — expose only the first table and will fail with *"The result contains multiple
tables"*. If you want that query in a workbook tile, split it into two single-table queries.

---

## Setting up cost alerts

![Alert Rule Configuration](./images/alert_rule.png)

1. Log Analytics workspace → **Alerts** → **Create → Alert rule**
2. Set the **Condition** to a custom log search:
   ```kql
   FinOpsAgentMetrics_CL
   | where AgentName_s == "super-fun-coding-learn-agent"
   | summarize TotalTokens = sum(TotalTokens_d) by UserDepartment_s, bin(TimeGenerated, 1h)
   | where TotalTokens > 20000
   ```
3. **Measure**: `TotalTokens`, **Aggregation**: Total, **Threshold**: Greater than `20000`
4. **Evaluation**: check every 1 hour over a 1-hour lookback
5. Attach an **Action group** (email, Teams webhook, or ITSM connector)
6. Name the rule and set severity, then **Create**

Tune the threshold per department rather than globally — a shared 20 K/hour ceiling will
either page constantly for Engineering or never fire for Finance.

---

## Project structure

```
finops-for-agents/
├── code/                          # Bot middleware (Python / Flask)
│   ├── bot_service.py             # HTTP entry point, request orchestration, REST read API
│   ├── utils.py                   # JWT decode + AAD token acquisition per scope
│   ├── user_metadata.py           # Teams activity + Microsoft Graph enrichment
│   ├── foundry_agent.py           # Foundry Responses API client, usage parsing
│   ├── pricing.py                 # Retail Prices API lookup + in-process cache
│   ├── finops_metrics.py          # FOCUS record build, validate, price, ship
│   ├── finops_query.py            # KQL reads over FinOpsAgentMetrics_CL (Entra ID)
│   ├── requirements.txt
│   └── SETUP.md                   # Detailed setup & troubleshooting guide
├── finops_data_layer/             # The reusable part
│   ├── schema.json                # FOCUS 1.0 + x_ extensions (JSON Schema 2020-12)
│   ├── finops_schema.py           # Typed builder + validator
│   ├── README.md                  # Field-by-field reference
│   └── USAGE.md                   # Integration examples
├── infra/                         # Terraform (Foundry, Log Analytics, App Insights, …)
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── example.tfvars
├── mcp_server/                    # MCP server over the cost data (Azure Functions, Python v2)
│   ├── function_app.py            # @app.mcp_tool definitions + KQL
│   ├── host.json                  # Functions host + MCP extension config
│   ├── local.settings.json        # Local settings (workspace id, storage)
│   └── requirements.txt
├── dashboards/
│   └── finops-dashboard.json      # Importable Azure Workbook
├── teams_app/                     # Teams manifest + icons
├── showcases/                     # Demo walkthroughs, screenshots and videos
└── images/                        # Screenshots and diagrams
```

---

## Known limitations

This is a working reference implementation, not a billing system. Before you put a number from
it in front of a finance team, know these:

**Department attribution is incomplete and not stable per user.** `UserDepartment_s` is written
per *record*, from whatever Graph returned at the time of the request — it is not a property of
the user. In the demo dataset that produces two distinct failures:

- Roughly **39% of tokens land in `N/A`**, where Graph enrichment did not resolve. `N/A` is a
  data-quality bucket, not a department, and treating it as one understates every real
  department.
- **One account appears under several departments.** A shared `admin@` account shows up as
  `N/A`, `IT Operations` *and* `Engineering` across different requests.

A practical consequence: `dcount(UserEmail_s)` grouped by department **double-counts people**,
because one user can appear in multiple buckets. Sum tokens, not headcount, until enrichment is
fixed.

**Cost is an estimate, not the invoice.** Pricing is hardcoded at `$0.00001/input` and
`$0.00003/output` in [`code/finops_metrics.py`](./code/finops_metrics.py). It is not per-model,
it does not price cached or reasoning tokens separately, and nothing reconciles it against the
actual Cognitive Services bill. Every `TotalCost` and `EffectiveCost_d` you see — in the
workbook, the REST API and the MCP tools — inherits that estimate. Token counts are exact; the
money is not.

**Ingestion is fire-and-forget.** A failed POST logs and drops the record. Totals are a floor,
not a guarantee.

**Retention is 90 days.** The workspace is provisioned with the default retention, so any
look-back beyond 90 days returns nothing regardless of the `days` argument you pass.

---

## Roadmap

The current implementation is a working end-to-end reference. These are the gaps between it
and a production deployment, roughly in priority order.

### Near term — production hardening

- [ ] **Move hardcoded configuration to environment variables.** `FOUNDRY_ENDPOINT` and
      `LOG_ANALYTICS_WORKSPACE_ID` are currently literals in the source.
- [ ] **Fix Graph enrichment so department is stable per user.** Today it is resolved per
      request and fails open to `N/A`, which is the root cause of the attribution problems in
      [Known limitations](#known-limitations). Cache the lookup per user, retry on failure, and
      keep unresolved users out of the department rollup rather than bucketing them as `N/A`.
- [ ] **Secure and deploy the MCP server.** `host.json` sets the MCP webhook to `Anonymous`,
      which is fine locally and unacceptable in Azure. Deploy it with Functions key or Entra ID
      auth and a managed identity holding **Log Analytics Reader**, rather than the developer's
      own credential.
- [ ] **Authenticate the REST read API.** `/api/departments` and `/api/{agent_name}/billing`
      are unauthenticated — fine behind `localhost`, not fine once the bot is hosted, since
      they expose per-department spend to anyone who can reach the port. Put them behind
      Entra ID auth or move them off the public Bot Framework listener.
- [ ] **Replace shared keys with managed identity.** The Data Collector API key should become
      a Managed Identity writing through
      [Log Analytics DCR-based ingestion](https://learn.microsoft.com/azure/azure-monitor/logs/logs-ingestion-api-overview),
      which also removes the deprecated HTTP Data Collector dependency — and lets you name the
      columns yourself instead of inheriting the `_s` / `_d` suffixes.
- [ ] **Deploy the bot as a service.** Today it runs locally behind a tunnel. Azure Container
      Apps or App Service with autoscaling is the natural target.
- [ ] **Buffer and retry ingestion.** Metric shipping is inline and fire-and-forget; a failed
      POST loses the record. Queue it.
- [ ] **Add a test suite.** Schema validation, response parsing and cost calculation are all
      pure functions and trivially testable.

### Medium term — cost accuracy

- [x] **Real pricing, not a flat rate.** Per-token rates are resolved per model from the
      Azure Retail Prices API ([`code/pricing.py`](./code/pricing.py)) and cached in-process
      for 24 hours. Each model needs an entry in the `METERS` map — meter names are not
      derivable from the model id.
- [x] **Price cached and reasoning tokens separately.** Cached input tokens are billed against
      the dedicated cached meter (a tenth of the input rate). Reasoning tokens have no separate
      meter in the Azure price catalogue — they are a subset of output tokens and correctly
      billed at the output rate, so they are recorded for visibility only.
- [ ] **Reconcile against the Azure invoice.** Attributed cost should tie back to the actual
      Cognitive Services bill; a monthly reconciliation job would surface drift.

### Longer term — platform

- [ ] **Additional entry points.** The pipeline assumes Teams. A generic REST ingress would let
      web apps, Copilot Studio and API callers attribute the same way.
- [ ] **Additional agent runtimes.** The schema is provider-agnostic; the client is not. Adapters
      for OpenAI, Anthropic and Bedrock would make the data layer genuinely portable.
- [ ] **Budgets and enforcement.** Per-department monthly caps with soft warnings and hard stops.
- [ ] **Broader MCP tool surface.** Two read tools exist today. Cost-per-model, month-over-month
      trend, and budget-remaining tools would let an assistant run most of a FinOps review
      unaided.
- [ ] **Cost centre mapping.** `x_CostCenter` exists in the schema but is not populated — wire it
      to the finance system's cost centre hierarchy rather than the Graph `department` string.
- [ ] **Export to FinOps tooling.** A scheduled FOCUS export to a cost management platform closes
      the loop with the rest of the organisation's FinOps practice.

---

## Contributing

Issues and pull requests are welcome. The most valuable contributions right now are
**additional agent runtime adapters** and **accurate pricing sources** — both are called out in
the roadmap above.

When contributing:

- Keep the FOCUS schema authoritative. New fields belong in `finops_data_layer/schema.json`
  with the `x_` prefix if they are not part of the FOCUS specification.
- Do not commit secrets. `code/.env` and `infra/terraform.tfvars` are git-ignored — keep them
  that way.

---

## References

- [FOCUS™ — FinOps Open Cost and Usage Specification](https://focus.finops.org/)
- [FinOps Foundation Framework](https://www.finops.org/framework/)
- [Microsoft Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Azure Monitor Logs ingestion API](https://learn.microsoft.com/azure/azure-monitor/logs/logs-ingestion-api-overview)
- [Model Context Protocol specification](https://modelcontextprotocol.io)
- [Azure Functions MCP extension](https://learn.microsoft.com/azure/azure-functions/functions-bindings-mcp)
- [KQL: `series_decompose_anomalies`](https://learn.microsoft.com/kusto/query/series-decompose-anomaliesfunction)

---

<div align="center">
<sub>Built for the Microsoft Hackathon 2026 · Aligned to FinOps Foundation standards</sub>
</div>

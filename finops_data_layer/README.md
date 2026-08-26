# FinOps for Agents - Data Layer

## Overview

The FinOps for Agents data layer extends the **FOCUS (FinOps Open Cost and Usage Specification)** framework to capture and standardize cost and usage metrics for AI agent deployments. This data layer enables organizations to track, attribute, and optimize AI agent costs at the user and team level using established FinOps practices.

## Purpose

This data layer serves as the foundation for:

- **Cost Attribution**: Assign agent usage costs to specific users, teams, departments, or business units
- **Usage Analytics**: Analyze token consumption, model selection, and agent performance
- **Financial Reporting**: Generate chargeback and showback reports aligned with FOCUS standards
- **Optimization**: Identify cost-saving opportunities and inefficient agent usage patterns
- **Compliance**: Maintain audit trails for governance and regulatory requirements

## Architecture

### Data Collection Flow

```
Microsoft Teams Message
    ↓
Azure Bot Service
    ↓
Python Middleware (Extract User Identity + Graph API Enrichment)
    ↓
Microsoft Foundry Agent (Process Request)
    ↓
Capture FOCUS-Extended Metrics
    ↓
Data Layer (Application Insights / Cosmos DB)
    ↓
FinOps Dashboards & Reports
```

### Schema & Column Definitions

The FinOps for Agents schema is based on **FOCUS 1.0** with agent-specific extensions. All columns are prefixed with `x_` to indicate non-standard FOCUS extensions.

#### Core Billing Dimensions (FOCUS Standard)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `BillingAccountId` | String | Unique identifier for the billing account | `99f1582e-0660-4cdb-8dac-21d7a4752603` |
| `BillingAccountName` | String | Display name of the billing account | `Contoso FinOps Hackathon` |
| `BillingPeriodStart` | DateTime | Start of billing period (inclusive) | `2026-08-01T00:00:00Z` |
| `BillingPeriodEnd` | DateTime | End of billing period (exclusive) | `2026-08-31T23:59:59Z` |
| `BillingCurrency` | String | Currency of the charge | `USD` |
| `ChargePeriodStart` | DateTime | Start of charge period (inclusive) | `2026-08-25T13:47:52Z` |
| `ChargePeriodEnd` | DateTime | End of charge period (exclusive) | `2026-08-25T13:47:57Z` |

#### Service & SKU Dimensions (FOCUS Standard)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `ServiceCategory` | String | Highest-level classification of service | `AI Services` |
| `ServiceName` | String | Specific AI service offering | `Microsoft Foundry` |
| `ServiceSubcategory` | String | Sub-classification of service | `AI Agents` |
| `SkuId` | String | Unique identifier for SKU | `gpt-5-mini` |
| `SkuMeterName` | String | Name of usage meter | `Token Processing` |
| `ResourceId` | String | Unique identifier for the resource | `super-fun-coding-learn-agent` |
| `ResourceName` | String | Display name of the resource | `super-fun-coding-learn-agent` |
| `ResourceType` | String | Type of resource | `AI Agent` |

#### Cost Dimensions (FOCUS Standard)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `ListCost` | Decimal | Undiscounted cost (list price × quantity) | `0.43` |
| `ListUnitPrice` | Decimal | Public list price per unit | `0.000101` |
| `EffectiveCost` | Decimal | Final cost after all discounts and amortization | `0.43` |
| `BilledCost` | Decimal | Invoiced cost before amortization | `0.43` |
| `ConsumedQuantity` | Decimal | Total units of service consumed | `4,816` |
| `ConsumedUnit` | String | Unit of measurement for consumption | `Tokens` |
| `PricingQuantity` | Decimal | Quantity used for pricing calculation | `4.816` |
| `PricingUnit` | String | Unit of measurement for pricing | `Thousand Tokens` |

#### User & Organization Dimensions (FOCUS Extension)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `x_UserId` | String | Unique identifier for the user (AAD Object ID) | `bb21c6ed-b5d7-4d44-8814-85ba26bed1f5` |
| `x_UserEmail` | String | Email address of the user | `admin@M365CPI58152658.onmicrosoft.com` |
| `x_UserName` | String | Display name of the user | `MOD Administrator` |
| `x_UserDepartment` | String | Department of the user | `Engineering` |
| `x_CostCenter` | String | Cost center for chargeback | `ENG-001` |
| `x_TeamId` | String | Team or business unit identifier | `Engineering-AI-Team` |
| `x_ProjectId` | String | Project or initiative identifier | `FinOps-Hackathon` |

#### Agent & Model Dimensions (FOCUS Extension)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `x_AgentId` | String | Unique identifier for the agent | `super-fun-coding-learn-agent` |
| `x_AgentName` | String | Display name of the agent | `super-fun-coding-learn-agent` |
| `x_AgentVersion` | String | Version of the agent deployment | `2` |
| `x_ModelId` | String | Unique identifier for the AI model | `gpt-5-mini` |
| `x_ModelName` | String | Display name of the AI model | `GPT-5 Mini` |
| `x_ModelFamily` | String | Family or class of the model | `OpenAI` |

#### Token & Usage Dimensions (FOCUS Extension)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `x_InputTokens` | Integer | Tokens consumed from the input/prompt | `4,339` |
| `x_OutputTokens` | Integer | Tokens generated in the response | `477` |
| `x_ReasoningTokens` | Integer | Tokens used for reasoning (if applicable) | `128` |
| `x_TotalTokens` | Integer | Sum of all token types | `4,816` |
| `x_TokensPerSecond` | Decimal | Token throughput (tokens / processing_time) | `963.2` |

#### Performance & Time Dimensions (FOCUS Extension)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `x_CreatedAt` | DateTime | UTC timestamp when interaction started | `2026-08-25T13:47:52Z` |
| `x_CompletedAt` | DateTime | UTC timestamp when interaction completed | `2026-08-25T13:47:57Z` |
| `x_ProcessingTimeSeconds` | Decimal | Total time to process request in seconds | `5` |
| `x_RequestId` | String | Unique identifier for the request | `resp_0a7542e13ef...` |

#### Metadata & Tagging Dimensions (FOCUS Standard)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `Tags` | JSON | Custom key-value pairs for tracking and filtering | `{"environment":"production","priority":"high"}` |
| `x_InteractionType` | String | Type of user-agent interaction | `Chat Message` |
| `x_Channel` | String | Communication channel used | `Microsoft Teams` |

#### Geographic & Infrastructure Dimensions (FOCUS Extension)

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `RegionId` | String | Azure region identifier | `Sweden Central` |
| `RegionName` | String | Display name of region | `Sweden Central` |
| `x_AvailabilityZone` | String | Availability zone within region | `swedencentral-1` |

---

## Sample Record

Example of a complete FinOps for Agents record in JSON format:

```json
{
  "BillingAccountId": "99f1582e-0660-4cdb-8dac-21d7a4752603",
  "BillingAccountName": "Contoso FinOps Hackathon",
  "BillingPeriodStart": "2026-08-01T00:00:00Z",
  "BillingPeriodEnd": "2026-08-31T23:59:59Z",
  "BillingCurrency": "USD",
  "ChargePeriodStart": "2026-08-25T13:47:52Z",
  "ChargePeriodEnd": "2026-08-25T13:47:57Z",
  "ServiceCategory": "AI Services",
  "ServiceName": "Microsoft Foundry",
  "ServiceSubcategory": "AI Agents",
  "SkuId": "gpt-5-mini",
  "SkuMeterName": "Token Processing",
  "ResourceId": "super-fun-coding-learn-agent",
  "ResourceName": "super-fun-coding-learn-agent",
  "ResourceType": "AI Agent",
  "ListCost": 0.43,
  "ListUnitPrice": 0.000101,
  "EffectiveCost": 0.43,
  "BilledCost": 0.43,
  "ConsumedQuantity": 4816,
  "ConsumedUnit": "Tokens",
  "PricingQuantity": 4.816,
  "PricingUnit": "Thousand Tokens",
  "x_UserId": "bb21c6ed-b5d7-4d44-8814-85ba26bed1f5",
  "x_UserEmail": "admin@M365CPI58152658.onmicrosoft.com",
  "x_UserName": "MOD Administrator",
  "x_UserDepartment": "N/A",
  "x_CostCenter": "ENG-001",
  "x_TeamId": "Engineering-AI-Team",
  "x_ProjectId": "FinOps-Hackathon",
  "x_AgentId": "super-fun-coding-learn-agent",
  "x_AgentName": "super-fun-coding-learn-agent",
  "x_AgentVersion": "2",
  "x_ModelId": "gpt-5-mini",
  "x_ModelName": "GPT-5 Mini",
  "x_ModelFamily": "OpenAI",
  "x_InputTokens": 4339,
  "x_OutputTokens": 477,
  "x_ReasoningTokens": 128,
  "x_TotalTokens": 4816,
  "x_TokensPerSecond": 963.2,
  "x_CreatedAt": "2026-08-25T13:47:52Z",
  "x_CompletedAt": "2026-08-25T13:47:57Z",
  "x_ProcessingTimeSeconds": 5,
  "x_RequestId": "resp_0a7542e13ef05c2f006a8d840fab988190b79fd3832e045ced",
  "Tags": {
    "environment": "production",
    "priority": "high"
  },
  "x_InteractionType": "Chat Message",
  "x_Channel": "Microsoft Teams",
  "RegionId": "swedencentral",
  "RegionName": "Sweden Central",
  "x_AvailabilityZone": "swedencentral-1"
}
```

---

## Reporting Queries

### Query 1: Total Spend by User

```sql
SELECT 
  x_UserEmail,
  x_UserName,
  SUM(BilledCost) as TotalCost,
  SUM(x_TotalTokens) as TotalTokens,
  COUNT(*) as InteractionCount
FROM FinOpsAgentMetrics
WHERE BillingPeriodStart >= @StartDate
GROUP BY x_UserEmail, x_UserName
ORDER BY TotalCost DESC
```

### Query 2: Cost by Agent and Model

```sql
SELECT 
  x_AgentName,
  x_AgentVersion,
  x_ModelName,
  SUM(BilledCost) as TotalCost,
  AVG(x_ProcessingTimeSeconds) as AvgProcessingTime,
  SUM(x_InputTokens) as TotalInputTokens,
  SUM(x_OutputTokens) as TotalOutputTokens
FROM FinOpsAgentMetrics
WHERE BillingPeriodStart >= @StartDate
GROUP BY x_AgentName, x_AgentVersion, x_ModelName
ORDER BY TotalCost DESC
```

### Query 3: Cost by Department and Team

```sql
SELECT 
  x_UserDepartment,
  x_TeamId,
  SUM(BilledCost) as TotalCost,
  COUNT(DISTINCT x_UserEmail) as UniqueUsers,
  AVG(x_TotalTokens) as AvgTokensPerInteraction
FROM FinOpsAgentMetrics
WHERE BillingPeriodStart >= @StartDate
GROUP BY x_UserDepartment, x_TeamId
ORDER BY TotalCost DESC
```

---

## Integration Points

### Data Collection

- **Source**: Python Flask bot middleware (code/bot_service.py)
- **Destination**: Application Insights or Cosmos DB
- **Frequency**: Real-time, one record per user-agent interaction
- **Retention**: 90+ days (Application Insights) or unlimited (Cosmos DB)

### Data Storage Options

| Option | Pros | Cons |
|--------|------|------|
| **Application Insights** | Built-in analytics, KQL queries, dashboards | 90-day retention limit, less structured |
| **Cosmos DB** | Unlimited retention, NoSQL flexibility | Query complexity, higher cost at scale |
| **Log Analytics** | Same as App Insights but with longer retention | Same query language learning curve |
| **Azure Data Lake** | Cost-effective at scale, data warehouse patterns | Requires ETL pipeline, more setup |

---

## FOCUS Compliance

This data layer follows the **FOCUS 1.0 specification** with the following extensions:

- **Agent-Specific Metrics**: Input/output/reasoning tokens, processing time, agent version
- **User Attribution**: Email, department, team, cost center for chargeback
- **Channel Integration**: Teams, channel type, interaction metadata
- **Model Tracking**: Model family, version, inference parameters

For more information on FOCUS, visit:
- [FOCUS Overview](https://learn.microsoft.com/en-us/cloud-computing/finops/focus/what-is-focus)
- [FOCUS Specification](https://focus.finops.org/)
- [FinOps Foundation](https://www.finops.org/)

---

## Next Steps

1. **Implement Data Collection**: Add instrumentation to bot_service.py to collect and send metrics
2. **Configure Storage**: Set up Application Insights or Cosmos DB for data persistence
3. **Build Dashboards**: Create Power BI or Application Insights dashboards for visualization
4. **Generate Reports**: Implement KQL queries for cost attribution and analysis
5. **Optimize**: Use insights to identify cost-saving opportunities and optimization opportunities


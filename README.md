# FinOps for Agents - A Hackathon Project

## Current Situation
AI agents enable organizations to automate processes, make knowledge more accessible, and empower employees to work more efficiently. At the same time, they introduce a new cost structure: in addition to infrastructure costs, usage-based expenses arise from token consumption, model calls, and agent executions.

## Challenge
Today, these costs are often captured centrally at the platform or agent level. The actual cost drivers — such as users, teams, applications, or business processes — often remain hidden. This makes it difficult to plan budgets, assess business value, and scale the productive use of AI agents in a controlled way.

## Solution Approach
FinOps for Agents builds on established and standardized FinOps practices. Existing models and approaches from the FinOps Foundation are extended and adapted to the specific requirements of agentic solutions. This includes agent-specific metrics such as token consumption, model usage, user interactions, and executions.

As a result, AI costs can be captured transparently and allocated to teams, applications, or business processes based on actual usage. The approach provides a compatible foundation for existing cloud FinOps processes, rather than creating an isolated cost model for AI agents.

## Business Value

Organizations gain a reliable basis for making informed decisions about the economic use of AI agents. They can identify which agents deliver the highest value, where optimization opportunities exist, and how AI investments can be managed more effectively. At the same time, the solution supports budgeting, showback, chargeback, reporting, and cost control.

By aligning with established FinOps standards, the approach can be integrated more easily into existing governance, controlling, and reporting structures.

## Target State

FinOps for Agents extends the model landscape of the FinOps Foundation by introducing a central interface for capturing agent-specific cost metrics. A realistic scenario is demonstrated using Microsoft Foundry as the agent runtime and Microsoft Teams and Microsoft 365 as entry points for user interactions. Additional components such as Azure API Management and a custom container app are addressed as part of the solution’s technical architecture.

Based on this data foundation, reports, dashboards, and automated analyses can be created. This enables organizations to operate agentic applications in a scalable, cost-effective, and financially sustainable way — built on established FinOps principles.

---

## Architecture Overview

The FinOps for Agents solution demonstrates a complete integration pipeline from Microsoft Teams to Microsoft Foundry agents, with comprehensive cost metrics capture.

```
Teams → Bot Service → Flask Middleware → Graph API → Foundry Agent → Teams
        (DevTunnel)    (Extract Identity)  (Enrich User)  (Process Request)
```

### Component Flow

1. **Microsoft Teams** (User Interface)
   - Users send messages through Teams chat
   - Receives agent responses with attached metadata

2. **Azure Bot Service** (Bot Framework)
   - Registered bot application (App ID: 3b9d4a32-20a4-44e3-b62a-46087da55e72)
   - Handles OAuth and message routing
   - Accessible locally via Azure DevTunnel

3. **Python Flask Middleware** (Identity Extraction)
   - Runs on port 3978
   - Extracts user identity from Teams activity:
     - Name, Teams User ID, AAD Object ID
   - Calls Microsoft Graph API for enrichment
   - Forwards enriched context to Foundry agent

4. **Microsoft Graph API** (User Data Enrichment)
   - Retrieves user profile data:
     - Email, Department, Job Title, Office Location, Mobile Phone
   - Requires Directory.Read.All and User.Read.All permissions (Application type)

5. **Microsoft Foundry Agent** (Agent Runtime)
   - Agent: `super-fun-coding-learn-agent` (version 2)
   - Model: `gpt-5-mini`
   - Processes user requests with awareness of user context
   - Returns response with token usage and execution metrics

6. **Azure Infrastructure** (Cloud Resources)
   - Region: Sweden Central
   - Storage Account (data)
   - Cosmos DB (persistence)
   - AI Search (knowledge base)
   - AI Foundry Hub (agent orchestration)

## Technology Stack

### Backend & Cloud
- **Cloud Platform**: Microsoft Azure (Sweden Central region)
- **Infrastructure as Code**: Terraform
- **Agent Runtime**: Microsoft Foundry (Azure AI Services)
- **Bot Framework**: Azure Bot Service
- **Local Middleware**: Python 3.11 + Flask 3.0.0

### APIs & Services
- **Microsoft Graph API** - User profile and directory data
- **Azure Bot Connector** - Bot-to-Teams communication
- **Foundry Responses Protocol** - Agent endpoint (OpenAI-compatible)

### Authentication & Security
- **Azure AD (Entra ID)** - OAuth 2.0 client credentials flow
- **Role-Based Access Control (RBAC)** - Foundry Agent Consumer role
- **Token Management** - Separate tokens for Bot Framework, Graph API, and Foundry

### Local Development
- **Azure DevTunnel** - Expose local bot service to internet
- **Python Dependencies**:
  - `botbuilder-core` & `botbuilder-schema` (Bot Framework SDK)
  - `aiohttp` & `requests` (HTTP clients)
  - `python-dotenv` (Environment configuration)

## Key Metrics Captured

For each user-agent interaction, the system captures:

| Metric | Source | Purpose |
|--------|--------|---------|
| **Model Used** | Foundry Response | Track which model is handling requests |
| **Input Tokens** | Token Usage Object | Measure context size and prompt length |
| **Output Tokens** | Token Usage Object | Quantify response generation cost |
| **Reasoning Tokens** | Token Usage Details | Isolate thinking/reasoning overhead |
| **Total Tokens** | Aggregated Usage | Complete cost calculation |
| **Processing Time** | Timestamps (created_at → completed_at) | Performance and latency tracking |
| **User Identity** | Teams Activity + Graph API | Cost attribution to teams/departments |
| **Agent Version** | Agent Reference | Version-specific performance analysis |
| **Timestamp** | Response Metadata | Historical cost trending |

## Data Flow for Cost Metrics

```
Teams Message
    ↓
[Extract] User metadata (name, AAD ID)
    ↓
[Enrich] Graph API call (email, department, phone)
    ↓
[Forward] To Foundry agent with full context
    ↓
[Receive] Response with:
  - Agent output text
  - Token usage (input/output/reasoning)
  - Processing time
  - Model and version info
    ↓
[Store] Metadata (attached to Teams response)
    ↓
[Report] Cost dashboard and chargeback reports
```

## Development & Deployment

### Local Development
```bash
# Set up environment
cd code
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env  # Add Bot App ID and Password

# Run locally
python bot_service.py

# Expose to internet
azd dev tunnel start
```

### Cloud Deployment
```bash
# Deploy infrastructure
cd ../infra
terraform init
terraform apply -var-file=terraform.tfvars

# Deploy bot service (Azure App Service or Container Apps)
# Configure Azure Bot Service to use Foundry agent endpoint
```

---
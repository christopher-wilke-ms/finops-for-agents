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

## Running the Solution Locally

### Prerequisites
- Python 3.11+
- Azure subscription with Foundry project
- Foundry agent created: `super-fun-coding-learn-agent`
- Azure Bot Service app registered (App ID: `3b9d4a32-20a4-44e3-b62a-46087da55e72`)
- Azure CLI or devtunnel CLI installed
- RBAC "Foundry Agent Consumer" role assigned to app registration on Foundry project

### Step 1: Set Up Python Environment

```bash
cd code

# Create virtual environment (Python 3.11)
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
# Create .env file with your credentials
cat > .env << EOF
BOT_APP_ID=3b9d4a32-20a4-44e3-b62a-46087da55e72
BOT_APP_PASSWORD=<your-bot-app-password>
EOF
```

### Step 3: Run Bot Service Locally

```bash
python bot_service.py
```

Expected output:
```
[INIT] Bot App ID: 3b9d4a32-20a4-44e3-b62a-46087da55e72
[INIT] Bot App Password: **********...
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:3978
```

### Step 4: Expose to Internet with DevTunnel

**In a new terminal:**

```bash
# Install devtunnel if needed
az dev tunnel create --allow-anonymous

# Start tunnel on port 3978
devtunnel host -a -p 3978
```

Expected output:
```
Tunnel URL: https://xxxx-xxxxx.devtunnels.ms
```

### Step 5: Configure Azure Bot Service Endpoint

1. Go to **Azure Portal**
2. Navigate to **Azure Bot Service** → Configuration
3. Update **Messaging endpoint** to:
   ```
   https://xxxx-xxxxx.devtunnels.ms/api/messages
   ```
4. Click **Save**

### Step 6: Test in Microsoft Teams

1. Open **Microsoft Teams**
2. Go to **Chat** → **+ New Chat**
3. Search for and add bot: `learning-python-agent`
4. Send a test message: `"hello"`

Expected Teams response:
```
**User Information:**
- Name: [Your Name]
- Email: [Your Email]
- Department: [Your Department]
- Office Location: [Your Office]

**Agent Response Metadata:**
- Model: gpt-5-mini
- Agent: super-fun-coding-learn-agent (v2)
- Input Tokens: [count]
- Output Tokens: [count]
- Total Tokens: [count]
- Created At: [timestamp]
- Completed At: [timestamp]
- Processing Time: [seconds]

**Final Request:**
hello

**Final Agent Response:**
[Agent's response here]
```

### Monitoring & Debugging

Watch the bot service terminal for logs:
```
[MESSAGE] Received POST to /api/messages
[MESSAGE] User: MOD Administrator
[GRAPH] Fetching user info from: https://graph.microsoft.com/v1.0/users/[ID]
[GRAPH] Response status: 200
[FOUNDRY] Calling agent at: https://aifoundry6449...
[FOUNDRY] Response status: 200
[FOUNDRY] Tokens - Input: 4337, Output: 515, Total: 4852
[REPLY] Successfully sent with user info!
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `devtunnel: command not found` | Install: `az dev tunnel create --allow-anonymous` |
| `403 Forbidden from Foundry` | Verify RBAC role assigned to app registration on Foundry project |
| `No response in Teams` | Check bot service logs, verify endpoint URL in Bot Service config |
| `Graph API 403 error` | Verify "Directory.Read.All" and "User.Read.All" permissions are "Granted for Contoso" |
| `venv activation fails` | Use Python 3.11: `python3.11 -m venv venv` |
| `Missing requirements` | Reinstall: `pip install -r requirements.txt --upgrade` |

---

## Cloud Deployment

### Step 1: Deploy Infrastructure

```bash
cd infra

# Initialize Terraform
terraform init

# Deploy to Azure (Sweden Central)
terraform apply -var-file=terraform.tfvars
```

### Step 2: Deploy Bot Service

```bash
# Option 1: Deploy to Azure Container Apps
azd provision
azd deploy

# Option 2: Deploy to Azure App Service
# Create an App Service and deploy the Flask application
```

### Step 3: Update Bot Service Endpoint

1. In Azure Portal, update Bot Service messaging endpoint to your deployed URL
2. Ensure Foundry agent is configured to accept traffic from the bot service identity

---
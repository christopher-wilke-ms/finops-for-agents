# FinOps for Agents - Bot Service Setup & Testing Guide

This guide will help you run the refactored bot service and test it from Microsoft Teams.

## Architecture Overview

The bot service has been refactored into modular components:

```
bot_service.py (Main Flask app - 60 lines)
├── utils.py (Token & JWT handling)
├── user_metadata.py (Teams + Graph API enrichment)
├── foundry_agent.py (Foundry agent calling)
├── finops_metrics.py (FinOps record creation & validation)
└── finops_data_layer/ (Schema & validation)
```

**Benefits:**
- ✅ Each module has single responsibility
- ✅ Fully documented with docstrings
- ✅ Easy to test and maintain
- ✅ Metrics integrated end-to-end

## Prerequisites

- Python 3.11+
- Azure subscription with resources deployed
- Bot App ID and Password (from your .env)
- Application Insights Instrumentation Key (from infrastructure deployment)
- Access to Microsoft Teams

## Setup Steps

### 1. Install Dependencies

```bash
cd code
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create/update `code/.env`:

```bash
cat > .env << 'EOF'
# Bot Framework
BOT_APP_ID=3b9d4a32-20a4-44e3-b62a-46087da55e72
BOT_APP_PASSWORD=<your-bot-app-password>

# FinOps Tracking
APPLICATIONINSIGHTS_INSTRUMENTATION_KEY=f1a1bc10-066e-42ba-b1ba-37b22a39b5ff
BILLING_ACCOUNT_ID=99f1582e-0660-4cdb-8dac-21d7a4752603
EOF
```

**Key environment variables:**
- `BOT_APP_ID`: From Azure Bot Service registration
- `BOT_APP_PASSWORD`: Bot app password (keep secure!)
- `APPLICATIONINSIGHTS_INSTRUMENTATION_KEY`: From infrastructure deployment output
- `BILLING_ACCOUNT_ID`: Your Azure subscription ID

### 3. Run the Bot Service Locally

**Terminal 1 - Start Flask bot service:**
```bash
cd code
source venv/bin/activate
python bot_service.py
```

Expected output:
```
[INIT] Bot App ID: 3b9d4a32-20a4-44e3-b62a-46087da55e72
[INIT] Bot App Password: **********...
[INIT] Starting Bot Service on http://0.0.0.0:3978
```

### 4. Expose Locally with DevTunnel

**Terminal 2 - Start DevTunnel:**
```bash
devtunnel host -a -p 3978
```

You'll get a URL like:
```
Tunnel URL: https://xxxx-xxxxx.devtunnels.ms
```

### 5. Configure Bot Endpoint in Azure

1. Go to **Azure Portal** → **Azure Bot Service**
2. Navigate to **Configuration**
3. Update **Messaging endpoint** to:
   ```
   https://xxxx-xxxxx.devtunnels.ms/api/messages
   ```
4. Click **Save**

### 6. Test from Microsoft Teams

#### Option A: Direct Chat (Recommended)

1. Open **Microsoft Teams**
2. Go to **Chat** → **New Chat** (or click **+**)
3. Search for bot: `learning-python-agent`
4. Click to start chat
5. Send a message: `hello` or `how to do a for loop in python?`
6. Wait for response (should include user info + agent response + metrics)

#### Option B: Add to Team Channel

1. In Teams, go to a channel
2. Click **+ Add apps**
3. Search for `learning-python-agent`
4. Install and configure

## Understanding the Response

When you send a message, the bot responds with a formatted message:

```
**User Information:**
- Name: John Doe
- Email: john@company.com
- Department: Engineering
- Office Location: Seattle

**Agent Response Metadata:**
- Model: gpt-5-mini
- Agent: super-fun-coding-learn-agent (v2)
- Input Tokens: 4,339
- Output Tokens: 477
- Total Tokens: 4,816
- Created At: 1787725832
- Completed At: 1787725837
- Processing Time: 5 seconds

**Final Request:**
hello

**Final Agent Response:**
Hey there! I'm ready to help. What would you like to know?
```

## Behind the Scenes: FinOps Metrics

For every message, the bot:

1. **Extracts** user identity from Teams JWT token
2. **Enriches** with Microsoft Graph API (email, department, etc.)
3. **Calls** Foundry agent and captures all metadata
4. **Creates** a FOCUS-compliant FinOps record with:
   - User email and department
   - Token counts (input, output, reasoning)
   - Model and agent version
   - Processing time and cost estimate
5. **Validates** against JSON Schema
6. **Sends** to Application Insights (Log Analytics backend)

Example console output:
```
[FINOPS] ========== FINOPS METRICS RECORDED ==========
[FINOPS] User: john@company.com
[FINOPS] Department: Engineering
[FINOPS] Agent: super-fun-coding-learn-agent (v2)
[FINOPS] Model: gpt-5-mini
[FINOPS] Input Tokens: 4,339
[FINOPS] Output Tokens: 477
[FINOPS] Total Tokens: 4,816
[FINOPS] Processing Time: 5 seconds
[FINOPS] Cost: $0.0043
[FINOPS] Request ID: resp_0a7542e13ef...
[FINOPS] =============================================
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'finops_data_layer'` | Ensure you're running from the `code` directory, and the parent directory contains `finops_data_layer/` |
| `401 Unauthorized` from Graph API | Check Bot App ID/Password and verify Graph API permissions are granted in Azure AD |
| `403 Forbidden` from Foundry | Verify app registration has "Foundry Agent Consumer" RBAC role on Foundry project |
| No response in Teams | Check devtunnel is running and endpoint URL is correctly configured in Bot Service settings |
| `Application Insights: Instrumentation key not configured` | Add `APPLICATIONINSIGHTS_INSTRUMENTATION_KEY` to `.env` |

## Next Steps

### Query FinOps Metrics in Log Analytics

Once data flows to Application Insights/Log Analytics, you can run KQL queries:

```kql
/* Total tokens by user */
FinOpsAgentMetrics
| where timestamp >= startofmonth(now())
| summarize TotalTokens=sum(x_TotalTokens) by x_UserEmail
| sort by TotalTokens desc

/* Cost by department */
FinOpsAgentMetrics
| where timestamp >= ago(30d)
| summarize Cost=sum(EffectiveCost), Interactions=count() by x_UserDepartment
| sort by Cost desc
```

### Build Power BI Dashboard

Connect Power BI to Log Analytics workspace for visual dashboards:
1. Power BI Desktop → Get Data → Azure
2. Select Log Analytics workspace
3. Query: FinOpsAgentMetrics table
4. Create visualizations (cost trends, user adoption, etc.)

## Code Structure

### bot_service.py (~60 lines)
- Flask app and message routing
- Orchestrates the flow
- Well-documented with docstrings

### utils.py (~100 lines)
- JWT token decoding
- Azure AD token acquisition
- Reusable token management

### user_metadata.py (~130 lines)
- Teams activity parsing
- Graph API integration
- User enrichment

### foundry_agent.py (~140 lines)
- Foundry agent API calls
- Response parsing
- Metadata extraction

### finops_metrics.py (~130 lines)
- FinOps record creation
- Schema validation
- Application Insights integration

## Support

For issues:
1. Check logs in bot service terminal
2. Verify .env variables are set correctly
3. Ensure DevTunnel is running
4. Check Bot Service endpoint configuration in Azure Portal
5. Verify application permissions in Azure AD app registration

import logging
import base64
import json
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from io import BytesIO

import azure.functions as func
from azure.functions.decorators.core import McpPropertyType
from mcp.types import ImageContent, TextContent, ContentBlock, ResourceLink, CallToolResult
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Log Analytics workspace holding the FOCUS-compliant agent cost records.
# Mirrors LOG_ANALYTICS_WORKSPACE_ID in code/finops_metrics.py, which is the
# writer side of this same table.
LOG_ANALYTICS_WORKSPACE_ID = os.getenv(
    "LOG_ANALYTICS_WORKSPACE_ID", "1704fbb7-e360-449c-af0b-ea430a93b9b8"
)
FINOPS_TABLE = "FinOpsAgentMetrics_CL"

# Agent names are interpolated into KQL, so constrain them to characters that
# cannot terminate a string literal or start a new statement.
AGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 ._-]{1,128}$")

_logs_client: Optional[LogsQueryClient] = None


def _get_logs_client() -> LogsQueryClient:
    """Return a cached LogsQueryClient.

    Built lazily so an import-time credential failure cannot take down the whole
    function app and unregister every other tool.
    """
    global _logs_client
    if _logs_client is None:
        _logs_client = LogsQueryClient(DefaultAzureCredential())
    return _logs_client


@app.mcp_tool()
def hello_mcp() -> str:
    """Hello world."""
    return "Hello I am MCPTool!"


@app.mcp_tool_trigger(
    arg_name="context",
    tool_name="my-random_tool",
    description="Returns a random number between 1 and 100.",
)
def my_random_tool(context: str) -> str:
    """Return a random number, and log the invocation to the host console."""
    number = random.randint(1, 100)
    logging.info("[MCP] >>> my-random_tool CALLED -> returning %s", number)
    return str(number)


@app.mcp_tool()
@app.mcp_tool_property(
    "agent_name",
    description=(
        "Exact agent name as recorded in the AgentName_s column, "
        "e.g. 'super-fun-coding-learn-agent'. Case-sensitive."
    ),
    property_type=McpPropertyType.STRING,
    is_required=True,
)
@app.mcp_tool_property(
    "days",
    description=(
        "Look-back window in days, counted back from now. Defaults to 30. "
        "The workspace retains 90 days, so values above 90 return no extra data."
    ),
    property_type=McpPropertyType.INTEGER,
    is_required=False,
)
def query_agent_usage_by_department(agent_name: str, days: int = 30) -> str:
    """Break down token consumption and cost per department for a single agent.

    Answers chargeback questions such as "which departments used
    'super-fun-coding-learn-agent' in the last 90 days".

    Queries the FinOpsAgentMetrics_CL table in Azure Log Analytics and returns one
    row per department with total tokens, input/output split, estimated cost,
    request count and distinct user count, sorted by total tokens descending.
    Departments that were never enriched from Microsoft Graph appear as "N/A".
    """
    # Arguments arrive as raw JSON, so a client may send days as "90" or 90.0.
    try:
        days = int(days)
    except (TypeError, ValueError):
        return json.dumps({"error": f"'days' must be a whole number, got {days!r}."})

    if not 1 <= days <= 730:
        return json.dumps({"error": f"'days' must be between 1 and 730, got {days}."})

    if not isinstance(agent_name, str) or not AGENT_NAME_PATTERN.match(agent_name):
        return json.dumps({
            "error": (
                "'agent_name' must be 1-128 characters of letters, digits, spaces, "
                "dots, underscores or hyphens."
            ),
            "received": str(agent_name),
        })

    query = f"""
    {FINOPS_TABLE}
    | where AgentName_s == "{agent_name}"
    | summarize
        TotalTokens  = sum(TotalTokens_d),
        InputTokens  = sum(InputTokens_d),
        OutputTokens = sum(OutputTokens_d),
        TotalCost    = sum(EffectiveCost_d),
        RequestCount = count(),
        UniqueUsers  = dcount(UserEmail_s)
        by Department = UserDepartment_s
    | sort by TotalTokens desc
    """

    logging.info(
        "[MCP] >>> query_agent_usage_by_department CALLED agent=%s days=%s",
        agent_name, days,
    )

    try:
        response = _get_logs_client().query_workspace(
            workspace_id=LOG_ANALYTICS_WORKSPACE_ID,
            query=query,
            timespan=timedelta(days=days),
        )
    except Exception as err:
        logging.exception("[MCP] Log Analytics query failed")
        return json.dumps({
            "error": "Log Analytics query failed.",
            "detail": str(err),
            "workspace_id": LOG_ANALYTICS_WORKSPACE_ID,
        })

    if response.status == LogsQueryStatus.FAILURE:
        return json.dumps({
            "error": "Log Analytics returned a query failure.",
            "detail": str(response.partial_error or "unknown"),
        })

    # A PARTIAL result still carries usable rows on response.partial_data.
    tables = response.partial_data if response.status == LogsQueryStatus.PARTIAL else response.tables
    departments = []
    for table in tables or []:
        for row in table.rows:
            departments.append(dict(zip(table.columns, row)))

    result = {
        "agent_name": agent_name,
        "days": days,
        "workspace_id": LOG_ANALYTICS_WORKSPACE_ID,
        "table": FINOPS_TABLE,
        "department_count": len(departments),
        "totals": {
            "TotalTokens": sum(d.get("TotalTokens") or 0 for d in departments),
            "TotalCost": round(sum(d.get("TotalCost") or 0 for d in departments), 6),
            "RequestCount": sum(d.get("RequestCount") or 0 for d in departments),
        },
        "departments": departments,
    }

    if not departments:
        result["note"] = (
            f"No records for agent '{agent_name}' in the last {days} days. "
            "Check the agent name spelling and that ingestion is running."
        )
    if response.status == LogsQueryStatus.PARTIAL:
        result["warning"] = f"Partial result: {response.partial_error}"

    return json.dumps(result, default=str)

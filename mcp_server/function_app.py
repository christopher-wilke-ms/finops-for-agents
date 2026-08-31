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
@app.mcp_tool_property(
    "top_n",
    description=(
        "How many users to return, ranked by total tokens descending. "
        "Defaults to 3. Must be between 1 and 50."
    ),
    property_type=McpPropertyType.INTEGER,
    is_required=False,
)
def query_agent_top_users(agent_name: str, days: int = 30, top_n: int = 3) -> str:
    """Rank the heaviest individual users of a single agent by token consumption.

    Answers questions such as "who are the top 3 users of
    'super-fun-coding-learn-agent'".

    Queries the FinOpsAgentMetrics_CL table in Azure Log Analytics and returns one
    row per user with total tokens, input/output split, estimated cost, request
    count and average cost per request, sorted by total tokens descending and
    truncated to top_n. Users whose email was never enriched from Microsoft Graph
    appear as "N/A".

    Also returns agent_totals covering *every* user, not just the returned ones, so
    each row's ShareOfAgentTokens is a share of the agent's full usage rather than a
    share of the truncated top_n.
    """
    # Arguments arrive as raw JSON, so a client may send days as "90" or 90.0.
    try:
        days = int(days)
    except (TypeError, ValueError):
        return json.dumps({"error": f"'days' must be a whole number, got {days!r}."})

    if not 1 <= days <= 730:
        return json.dumps({"error": f"'days' must be between 1 and 730, got {days}."})

    try:
        top_n = int(top_n)
    except (TypeError, ValueError):
        return json.dumps({"error": f"'top_n' must be a whole number, got {top_n!r}."})

    if not 1 <= top_n <= 50:
        return json.dumps({"error": f"'top_n' must be between 1 and 50, got {top_n}."})

    if not isinstance(agent_name, str) or not AGENT_NAME_PATTERN.match(agent_name):
        return json.dumps({
            "error": (
                "'agent_name' must be 1-128 characters of letters, digits, spaces, "
                "dots, underscores or hyphens."
            ),
            "received": str(agent_name),
        })

    # Two result tables from one round trip: the top_n rows, plus totals across all
    # users. Without the second table we could not tell whether the top 3 represent
    # most of the agent's spend or a sliver of a long tail.
    query = f"""
    let per_user = {FINOPS_TABLE}
    | where AgentName_s == "{agent_name}"
    | summarize
        TotalTokens       = sum(TotalTokens_d),
        InputTokens       = sum(InputTokens_d),
        OutputTokens      = sum(OutputTokens_d),
        TotalCost         = sum(EffectiveCost_d),
        RequestCount      = count(),
        AvgCostPerRequest = avg(EffectiveCost_d)
        by UserEmail = iff(isempty(UserEmail_s), "N/A", UserEmail_s);
    per_user
    | top {top_n} by TotalTokens desc;
    per_user
    | summarize
        AllUsers    = count(),
        AllTokens   = sum(TotalTokens),
        AllCost     = sum(TotalCost),
        AllRequests = sum(RequestCount)
    """

    logging.info(
        "[MCP] >>> query_agent_top_users CALLED agent=%s days=%s top_n=%s",
        agent_name, days, top_n,
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

    # Identify the totals table by its columns rather than by position, so a change
    # in statement order cannot silently swap the two.
    users: List[dict] = []
    totals: Optional[dict] = None
    for table in tables or []:
        if "AllTokens" in table.columns:
            if table.rows:
                totals = dict(zip(table.columns, table.rows[0]))
            continue
        for row in table.rows:
            users.append(dict(zip(table.columns, row)))

    all_tokens = (totals or {}).get("AllTokens") or 0
    for user in users:
        user["ShareOfAgentTokens"] = (
            round((user.get("TotalTokens") or 0) / all_tokens, 4) if all_tokens else None
        )

    result = {
        "agent_name": agent_name,
        "days": days,
        "top_n": top_n,
        "workspace_id": LOG_ANALYTICS_WORKSPACE_ID,
        "table": FINOPS_TABLE,
        "user_count": len(users),
        "agent_totals": {
            "UniqueUsers": (totals or {}).get("AllUsers", 0),
            "TotalTokens": all_tokens,
            "TotalCost": round((totals or {}).get("AllCost") or 0, 6),
            "RequestCount": (totals or {}).get("AllRequests", 0),
        },
        "top_users": users,
    }

    if not users:
        result["note"] = (
            f"No records for agent '{agent_name}' in the last {days} days. "
            "Check the agent name spelling and that ingestion is running."
        )
    if response.status == LogsQueryStatus.PARTIAL:
        result["warning"] = f"Partial result: {response.partial_error}"

    return json.dumps(result, default=str)

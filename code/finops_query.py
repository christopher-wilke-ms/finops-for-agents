"""
FinOps metrics querying from Azure Log Analytics.

This module is the read side of the same FinOpsAgentMetrics_CL table that
finops_metrics.py writes to. It handles:
- Authenticating to the Log Analytics query API via Entra ID
- Running KQL aggregations over agent cost records
- Shaping results into JSON-serialisable dictionaries

Note:
    Querying uses a different credential than ingestion. The Data Collector API
    in finops_metrics.py signs requests with LOG_ANALYTICS_SHARED_KEY, but
    api.loganalytics.io only accepts Entra ID bearer tokens, so this module uses
    DefaultAzureCredential (az login locally, managed identity when hosted).
    The caller needs the Log Analytics Reader role on the workspace.

Environment Variables:
    LOG_ANALYTICS_WORKSPACE_ID: Workspace GUID holding FinOpsAgentMetrics_CL
"""

import os
import re
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

from dotenv import load_dotenv
load_dotenv()

# Mirrors LOG_ANALYTICS_WORKSPACE_ID in finops_metrics.py, which is the writer
# side of this same table.
LOG_ANALYTICS_WORKSPACE_ID = os.getenv(
    "LOG_ANALYTICS_WORKSPACE_ID", "1704fbb7-e360-449c-af0b-ea430a93b9b8"
)
FINOPS_TABLE = "FinOpsAgentMetrics_CL"

DEFAULT_AGENT_NAME = "super-fun-coding-learn-agent"
DEFAULT_LOOKBACK_DAYS = 90
DEFAULT_CURRENCY = "USD"

# Agent names are interpolated into KQL, so constrain them to characters that
# cannot terminate a string literal or start a new statement.
AGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 ._-]{1,128}$")

_logs_client: Optional[LogsQueryClient] = None


def _get_logs_client() -> LogsQueryClient:
    """
    Return a cached LogsQueryClient.

    Built lazily so a missing or expired credential surfaces as a normal request
    error instead of stopping the Flask app from starting.

    Returns:
        Authenticated LogsQueryClient for the Log Analytics query API
    """
    global _logs_client
    if _logs_client is None:
        print("[FINOPSQUERY] Creating LogsQueryClient with DefaultAzureCredential")
        _logs_client = LogsQueryClient(DefaultAzureCredential())
    return _logs_client


def query_agent_usage_by_department(
    agent_name: str = DEFAULT_AGENT_NAME,
    days: int = DEFAULT_LOOKBACK_DAYS
) -> Tuple[Dict[str, Any], int]:
    """
    Break down token consumption and cost per department for a single agent.

    Answers chargeback questions such as "which departments used
    'super-fun-coding-learn-agent'". Returns one row per department with total
    tokens, the input/output split, estimated cost, request count and distinct
    user count, sorted by total tokens descending.

    Args:
        agent_name: Exact value of the AgentName_s column (case-sensitive)
        days: Look-back window in days, counted back from now

    Returns:
        Tuple of (payload, http_status)
        - payload: Result dictionary, or {"error": ..., ...} on failure
        - http_status: 200 on success, 400 on bad input, 502 on query failure

    Note:
        Departments never enriched from Microsoft Graph appear as "N/A".
    """
    # Query string arguments arrive as text, so accept "90" as well as 90.
    try:
        days = int(days)
    except (TypeError, ValueError):
        return {"error": f"'days' must be a whole number, got {days!r}."}, 400

    if not 1 <= days <= 730:
        return {"error": f"'days' must be between 1 and 730, got {days}."}, 400

    if not isinstance(agent_name, str) or not AGENT_NAME_PATTERN.match(agent_name):
        return {
            "error": (
                "'agent_name' must be 1-128 characters of letters, digits, spaces, "
                "dots, underscores or hyphens."
            ),
            "received": str(agent_name),
        }, 400

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
        by Department = iff(isempty(UserDepartment_s), "N/A", UserDepartment_s)
    | sort by TotalTokens desc
    """

    print(f"[FINOPSQUERY] Querying departments for agent={agent_name} days={days}")

    try:
        response = _get_logs_client().query_workspace(
            workspace_id=LOG_ANALYTICS_WORKSPACE_ID,
            query=query,
            timespan=timedelta(days=days),
        )
    except Exception as err:
        print(f"[ERROR] Log Analytics query failed: {err}")
        return {
            "error": "Log Analytics query failed.",
            "workspace_id": LOG_ANALYTICS_WORKSPACE_ID,
        }, 502

    if response.status == LogsQueryStatus.FAILURE:
        print(f"[ERROR] Log Analytics returned a failure: {response.partial_error}")
        return {
            "error": "Log Analytics returned a query failure.",
        }, 502

    # A PARTIAL result still carries usable rows on response.partial_data.
    tables = (
        response.partial_data
        if response.status == LogsQueryStatus.PARTIAL
        else response.tables
    )

    departments: List[Dict[str, Any]] = []
    for table in tables or []:
        for row in table.rows:
            departments.append(dict(zip(table.columns, row)))

    result: Dict[str, Any] = {
        "agent_name": agent_name,
        "days": days,
        "workspace_id": LOG_ANALYTICS_WORKSPACE_ID,
        "table": FINOPS_TABLE,
        "department_count": len(departments),
        "totals": {
            "TotalTokens": sum(d.get("TotalTokens") or 0 for d in departments),
            "InputTokens": sum(d.get("InputTokens") or 0 for d in departments),
            "OutputTokens": sum(d.get("OutputTokens") or 0 for d in departments),
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
        result["warning"] = "Partial result from Log Analytics."

    print(f"[FINOPSQUERY] Returned {len(departments)} department(s)")
    return result, 200


def query_agent_billing(
    agent_name: str = DEFAULT_AGENT_NAME,
    department: Optional[str] = None,
    days: int = DEFAULT_LOOKBACK_DAYS
) -> Tuple[Dict[str, Any], int]:
    """
    Cost breakdown for a single agent, optionally narrowed to one department.

    The chargeback view of query_agent_usage_by_department: same underlying rows,
    but led by cost rather than tokens, with each department's share of the agent's
    spend and its average cost per request.

    Args:
        agent_name: Exact value of the AgentName_s column (case-sensitive)
        department: Department to report on, matched case-insensitively.
                    None or blank returns every department.
        days: Look-back window in days, counted back from now

    Returns:
        Tuple of (payload, http_status)
        - payload: Billing dictionary, or {"error": ..., ...} on failure
        - http_status: 200 on success, 400 on bad input, 502 on query failure

    Note:
        The department filter is applied here rather than in KQL. That keeps the
        value out of the query text entirely, and it lets CostShare stay a share of
        the agent's whole spend instead of a share of the filtered rows, which would
        always be 100%.
    """
    usage, status = query_agent_usage_by_department(agent_name=agent_name, days=days)
    if status != 200:
        return usage, status

    agent_total_cost = usage["totals"]["TotalCost"]
    rows = usage["departments"]

    wanted = (department or "").strip()
    if wanted:
        rows = [
            row for row in rows
            if (row.get("Department") or "").casefold() == wanted.casefold()
        ]

    billing: List[Dict[str, Any]] = []
    for row in rows:
        cost = row.get("TotalCost") or 0
        request_count = row.get("RequestCount") or 0
        billing.append({
            "Department": row.get("Department"),
            "Cost": round(cost, 6),
            "CostShare": round(cost / agent_total_cost, 4) if agent_total_cost else 0,
            "AvgCostPerRequest": round(cost / request_count, 6) if request_count else 0,
            "TotalTokens": row.get("TotalTokens"),
            "InputTokens": row.get("InputTokens"),
            "OutputTokens": row.get("OutputTokens"),
            "RequestCount": request_count,
            "UniqueUsers": row.get("UniqueUsers"),
        })

    result: Dict[str, Any] = {
        "agent_name": agent_name,
        "department": wanted or None,
        "days": usage["days"],
        "currency": DEFAULT_CURRENCY,
        "workspace_id": LOG_ANALYTICS_WORKSPACE_ID,
        "table": FINOPS_TABLE,
        "department_count": len(billing),
        "billed_cost": round(sum(b["Cost"] for b in billing), 6),
        "agent_total_cost": agent_total_cost,
        "cost_basis": (
            "Estimate from the hardcoded rates in finops_metrics.py. "
            "Not reconciled against the Azure invoice."
        ),
        "billing": billing,
    }

    if wanted and not billing:
        known = sorted(
            {row.get("Department") or "" for row in usage["departments"]}
        )
        result["note"] = (
            f"No records for department '{wanted}' on agent '{agent_name}' in the "
            f"last {usage['days']} days. "
            f"Departments with usage: {', '.join(known) if known else 'none'}."
        )
    elif "note" in usage:
        result["note"] = usage["note"]

    if "warning" in usage:
        result["warning"] = usage["warning"]

    print(
        f"[FINOPSQUERY] Billing for agent={agent_name} "
        f"department={wanted or 'all'}: {len(billing)} row(s)"
    )
    return result, 200

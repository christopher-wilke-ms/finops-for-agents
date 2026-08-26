"""
FinOps metrics collection and Application Insights integration.

This module handles:
- Creating FinOps records from agent responses
- Validating records against JSON Schema
- Sending metrics to Application Insights for analysis
"""

import os
import sys
import json
import requests
import hmac
import hashlib
import base64
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import finops_data_layer (parent directory)
try:
    from finops_data_layer import FinOpsAgentMetrics, validate_record
except ImportError:
    # Fallback if running from different directory
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from finops_data_layer import FinOpsAgentMetrics, validate_record

# Application Insights configuration
APPINSIGHTS_KEY = os.getenv("APPLICATIONINSIGHTS_INSTRUMENTATION_KEY")
BILLING_ACCOUNT_ID = os.getenv("BILLING_ACCOUNT_ID", "99f1582e-0660-4cdb-8dac-21d7a4752603")

# Log Analytics configuration
LOG_ANALYTICS_WORKSPACE_ID = "1704fbb7-e360-449c-af0b-ea430a93b9b8"
LOG_ANALYTICS_SHARED_KEY = os.getenv("LOG_ANALYTICS_SHARED_KEY", "")
LOG_ANALYTICS_CUSTOM_LOG_NAME = "FinOpsAgentMetrics_CL"


def create_finops_record(
    foundry_metadata: Dict[str, Any],
    user_metadata: Dict[str, str],
    user_message: str,
    aad_object_id: str,
    graph_user_info: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    """
    Create a FinOps record from agent response and user metadata.

    Builds a FOCUS-compliant record with all cost attribution data:
    - User identity (email, department, AAD ID)
    - Agent and model information
    - Token usage metrics
    - Processing time
    - Cost estimation

    Args:
        foundry_metadata: Token usage and timing from Foundry response
        user_metadata: User context dictionary
        user_message: Original user query
        aad_object_id: Azure AD Object ID of the user
        graph_user_info: Enriched profile from Graph API

    Returns:
        FinOps record dictionary, or None on validation failure
    """
    try:
        from finops_data_layer import FinOpsAgentMetrics

        # Calculate token costs (example pricing)
        input_tokens = foundry_metadata.get('input_tokens', 0)
        output_tokens = foundry_metadata.get('output_tokens', 0)
        total_tokens = foundry_metadata.get('total_tokens', 0)

        # Simple cost model (adjust based on actual pricing)
        input_price = 0.00001  # $0.00001 per input token
        output_price = 0.00003  # $0.00003 per output token
        estimated_cost = (input_tokens * input_price) + (output_tokens * output_price)

        # Get current billing period dates
        now = datetime.now()
        billing_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            billing_end = billing_start.replace(year=now.year + 1, month=1)
        else:
            billing_end = billing_start.replace(month=now.month + 1)

        # Create FinOps record with parsed metadata
        record = FinOpsAgentMetrics(
            billing_account_id=BILLING_ACCOUNT_ID,
            billing_account_name="Contoso FinOps Hackathon",
            billing_period_start=billing_start.isoformat() + "Z",
            billing_period_end=billing_end.isoformat() + "Z",
            billing_currency="USD",
            charge_period_start=datetime.fromtimestamp(foundry_metadata.get('created_at', 0)).isoformat() + "Z" if foundry_metadata.get('created_at') else datetime.now().isoformat() + "Z",
            charge_period_end=datetime.fromtimestamp(foundry_metadata.get('completed_at', 0)).isoformat() + "Z" if foundry_metadata.get('completed_at') else datetime.now().isoformat() + "Z",
            service_category="AI Services",
            service_name="Microsoft Foundry",
            service_subcategory="AI Agents",
            sku_id=foundry_metadata.get('model', 'unknown'),
            sku_meter_name="Token Processing",
            resource_id=foundry_metadata.get('agent_name', 'unknown'),
            resource_name=foundry_metadata.get('agent_name', 'unknown'),
            resource_type="AI Agent",
            consumed_quantity=total_tokens,
            consumed_unit="Tokens",
            effective_cost=estimated_cost,
            user_id=aad_object_id,
            user_email=user_metadata.get('email', 'N/A'),
            user_name=user_metadata.get('name', 'N/A'),
            user_department=user_metadata.get('department', 'N/A'),
            agent_id=foundry_metadata.get('agent_name', 'unknown'),
            agent_name=foundry_metadata.get('agent_name', 'unknown'),
            agent_version=str(foundry_metadata.get('agent_version', 'unknown')),
            model_id=foundry_metadata.get('model', 'unknown'),
            model_name=f"GPT Model ({foundry_metadata.get('model', 'unknown')})",
            model_family="OpenAI",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            tokens_per_second=total_tokens / foundry_metadata.get('processing_time_seconds', 1) if foundry_metadata.get('processing_time_seconds', 0) > 0 else 0,
            created_at=datetime.fromtimestamp(foundry_metadata.get('created_at', 0)).isoformat() + "Z" if foundry_metadata.get('created_at') else datetime.now().isoformat() + "Z",
            completed_at=datetime.fromtimestamp(foundry_metadata.get('completed_at', 0)).isoformat() + "Z" if foundry_metadata.get('completed_at') else datetime.now().isoformat() + "Z",
            processing_time_seconds=foundry_metadata.get('processing_time_seconds', 0),
            request_id=foundry_metadata.get('response_id', 'unknown'),
            tags={"source": "teams_agent", "version": "1.0"},
            interaction_type="Chat Message",
            channel="Microsoft Teams",
            region_id="swedencentral",
            region_name="Sweden Central"
        )

        return record.to_dict()

    except Exception as err:
        print(f"[ERROR] Failed to create FinOps record: {err}")
        import traceback
        traceback.print_exc()
        return None


def validate_finops_record(record: Dict[str, Any]) -> Tuple[bool, list]:
    """
    Validate a FinOps record against JSON Schema.

    Args:
        record: FinOps record dictionary

    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: Boolean indicating if record passed validation
        - error_messages: List of validation error strings

    Note:
        Records are validated against finops_data_layer/schema.json
    """
    return validate_record(record)


def _build_log_analytics_signature(workspace_id: str, shared_key: str, date: str, content_length: int) -> str:
    """Build authorization signature for Log Analytics Data Collector API."""
    string_to_hash = f"POST\n{content_length}\napplication/json\nx-ms-date:{date}\n/api/logs"
    bytes_to_hash = bytes(string_to_hash, encoding="utf-8")
    decoded_key = base64.b64decode(shared_key)
    encoded_hash = base64.b64encode(
        hmac.new(decoded_key, bytes_to_hash, hashlib.sha256).digest()
    ).decode()
    return f"SharedKey {workspace_id}:{encoded_hash}"


def send_to_application_insights(record: Dict[str, Any]) -> bool:
    """
    Send FinOps record to Log Analytics via Data Collector API.

    Args:
        record: Validated FinOps record dictionary

    Returns:
        Boolean indicating if record was sent successfully
    """
    try:
        if not LOG_ANALYTICS_SHARED_KEY:
            print(f"[APPINSIGHTS] Log Analytics shared key not configured")
            print(f"[APPINSIGHTS] Set LOG_ANALYTICS_SHARED_KEY in .env file")
            return False

        # Prepare the payload for Log Analytics
        log_entry = {
            "Timestamp": datetime.utcnow().isoformat() + "Z",
            "UserEmail": str(record.get('x_UserEmail', 'N/A')),
            "UserDepartment": str(record.get('x_UserDepartment', 'N/A')),
            "AgentName": str(record.get('x_AgentName', 'N/A')),
            "AgentVersion": str(record.get('x_AgentVersion', 'N/A')),
            "ModelId": str(record.get('x_ModelId', 'N/A')),
            "RequestId": str(record.get('x_RequestId', 'N/A')),
            "InputTokens": float(record.get('x_InputTokens', 0)),
            "OutputTokens": float(record.get('x_OutputTokens', 0)),
            "TotalTokens": float(record.get('x_TotalTokens', 0)),
            "EffectiveCost": float(record.get('EffectiveCost', 0)),
            "ProcessingTimeSeconds": float(record.get('x_ProcessingTimeSeconds', 0)),
        }

        body = json.dumps(log_entry)
        content_length = len(body)

        # Create authorization header
        rfc1123date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        signature = _build_log_analytics_signature(
            LOG_ANALYTICS_WORKSPACE_ID,
            LOG_ANALYTICS_SHARED_KEY,
            rfc1123date,
            content_length
        )

        # Send to Log Analytics
        url = f"https://{LOG_ANALYTICS_WORKSPACE_ID}.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"
        headers = {
            "Content-Type": "application/json",
            "Authorization": signature,
            "Log-Type": LOG_ANALYTICS_CUSTOM_LOG_NAME,
            "x-ms-date": rfc1123date,
            "time-generated-field": "Timestamp",
        }

        response = requests.post(url, data=body, headers=headers, timeout=5)

        if response.status_code == 200:
            print(f"[APPINSIGHTS] ✅ Sent FinOps record to Log Analytics")
            print(f"[APPINSIGHTS] User: {record.get('x_UserEmail', 'N/A')}")
            print(f"[APPINSIGHTS] Tokens: {record.get('x_TotalTokens', 0):,}")
            print(f"[APPINSIGHTS] Cost: ${record.get('EffectiveCost', 0):.4f}")
            return True
        else:
            print(f"[APPINSIGHTS] Failed to send: HTTP {response.status_code}")
            print(f"[APPINSIGHTS] Response: {response.text[:200]}")
            return False

    except Exception as err:
        print(f"[ERROR] Failed to send to Log Analytics: {err}")
        return False






def log_finops_metrics(record: Dict[str, Any]) -> None:
    """
    Log FinOps metrics for immediate visibility.

    Prints formatted FinOps record to console for debugging and monitoring.

    Args:
        record: FinOps record dictionary
    """
    print(f"""
[FINOPS] ========== FINOPS METRICS RECORDED ==========
[FINOPS] User: {record.get('x_UserEmail', 'N/A')}
[FINOPS] Department: {record.get('x_UserDepartment', 'N/A')}
[FINOPS] Agent: {record.get('x_AgentName', 'N/A')} (v{record.get('x_AgentVersion', 'N/A')})
[FINOPS] Model: {record.get('x_ModelId', 'N/A')}
[FINOPS] Input Tokens: {record.get('x_InputTokens', 0):,}
[FINOPS] Output Tokens: {record.get('x_OutputTokens', 0):,}
[FINOPS] Total Tokens: {record.get('x_TotalTokens', 0):,}
[FINOPS] Processing Time: {record.get('x_ProcessingTimeSeconds', 0)} seconds
[FINOPS] Cost: ${record.get('EffectiveCost', 0):.4f}
[FINOPS] Request ID: {record.get('x_RequestId', 'N/A')}
[FINOPS] =============================================
""")

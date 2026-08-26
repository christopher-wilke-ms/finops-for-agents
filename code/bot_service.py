"""
FinOps for Agents - Bot Service

Main Flask application for receiving Teams messages, enriching user context,
calling Foundry agents, and tracking FinOps metrics.

This service acts as middleware between Teams and Microsoft Foundry agents,
providing:
- User identity extraction from Teams activity
- User profile enrichment via Graph API
- Foundry agent orchestration
- FinOps cost tracking and metrics collection

Environment Variables:
    BOT_APP_ID: Azure Bot Service app registration ID
    BOT_APP_PASSWORD: Bot app registration password
    APPLICATIONINSIGHTS_INSTRUMENTATION_KEY: App Insights key for metrics
    BILLING_ACCOUNT_ID: Azure billing account ID for cost tracking
"""

import os
from flask import Flask, request, jsonify
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter

from utils import get_bot_framework_token
from user_metadata import extract_user_metadata_from_activity, get_user_info_from_graph, build_user_metadata_dict
from foundry_agent import call_foundry_agent
from finops_metrics import create_finops_record, validate_finops_record, send_to_application_insights, log_finops_metrics

# Load environment
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

BOT_APP_ID = os.getenv("BOT_APP_ID")
BOT_APP_PASSWORD = os.getenv("BOT_APP_PASSWORD")

print(f"[INIT] Bot App ID: {BOT_APP_ID}")
print(f"[INIT] Bot App Password: {'*' * 10}...")

settings = BotFrameworkAdapterSettings(
    app_id=BOT_APP_ID,
    app_password=BOT_APP_PASSWORD
)

adapter = BotFrameworkAdapter(settings)


@app.route("/api/messages", methods=["POST"])
def messages():
    """
    Bot Framework message endpoint.

    Receives messages from Teams, extracts user context, calls Foundry agent,
    and sends response with FinOps metrics.

    Flow:
    1. Extract user metadata from Teams activity
    2. Enrich with Graph API profile data
    3. Call Foundry agent with message
    4. Create and validate FinOps record
    5. Send metrics to Application Insights
    6. Reply to Teams with formatted response

    Returns:
        Empty response (200 OK)
    """
    print(f"[MESSAGE] Received POST to /api/messages")

    # Validate content type
    if "application/json" not in request.headers.get("Content-Type", ""):
        return ("Unsupported Media Type", 415)

    body = request.get_json()
    user_name = body.get("from", {}).get("name")
    print(f"[MESSAGE] User: {user_name}")

    # Extract metadata
    auth_header = request.headers.get("Authorization", "")
    metadata = extract_user_metadata_from_activity(body, auth_header)

    # Build user context
    user_from = metadata.get("from_activity", {})
    aad_object_id = metadata.get("aad_object_id", "N/A")

    # Fetch enriched user info from Graph API
    graph_user_info = {}
    if aad_object_id != "N/A":
        graph_user_info = get_user_info_from_graph(aad_object_id) or {}

    # Build user metadata for agent
    user_metadata = build_user_metadata_dict(user_from, graph_user_info)

    # Call Foundry agent
    user_message = body.get('text', '')
    print(f"[MESSAGE] Calling Foundry agent with message: {user_message}")
    agent_response, agent_metadata = call_foundry_agent(user_message, user_metadata)

    # Create FinOps record
    finops_record = create_finops_record(
        foundry_metadata=agent_metadata,
        user_metadata=user_metadata,
        user_message=user_message,
        aad_object_id=aad_object_id,
        graph_user_info=graph_user_info
    )

    # Validate and send metrics
    if finops_record:
        is_valid, errors = validate_finops_record(finops_record)
        if is_valid:
            log_finops_metrics(finops_record)
            send_to_application_insights(finops_record)
        else:
            print(f"[FINOPS] Validation errors: {errors}")
    else:
        print(f"[FINOPS] Failed to create record")

    # Format response for Teams
    response_text = f"""**User Information:**
- Name: {user_from.get('name', 'N/A')}
- Email: {graph_user_info.get('mail', 'N/A')}
- Department: {graph_user_info.get('department', 'N/A')}
- Office Location: {graph_user_info.get('officeLocation', 'N/A')}

**Agent Response Metadata:**
- Model: {agent_metadata.get('model', 'N/A')}
- Agent: {agent_metadata.get('agent_name', 'N/A')} (v{agent_metadata.get('agent_version', 'N/A')})
- Input Tokens: {agent_metadata.get('input_tokens', 0):,}
- Output Tokens: {agent_metadata.get('output_tokens', 0):,}
- Total Tokens: {agent_metadata.get('total_tokens', 0):,}
- Created At: {agent_metadata.get('created_at', 'N/A')}
- Completed At: {agent_metadata.get('completed_at', 'N/A')}
- Processing Time: {agent_metadata.get('processing_time_seconds', 0)} seconds

**Final Request:**
{user_message}

**Final Agent Response:**
{agent_response}"""

    # Send response to Teams
    token = get_bot_framework_token()
    if not token:
        print(f"[ERROR] Could not get access token")
        return ("", 200)

    try:
        service_url = body.get("serviceUrl")
        conversation_id = body.get("conversation", {}).get("id")
        reply_to_id = body.get("id")

        reply_activity = {
            "type": "message",
            "text": response_text,
            "replyToId": reply_to_id
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = f"{service_url}v3/conversations/{conversation_id}/activities/{reply_to_id}"

        import requests
        resp = requests.post(url, json=reply_activity, headers=headers, timeout=10)

        print(f"[REPLY] Response status: {resp.status_code}")
        if resp.status_code in [200, 201]:
            print(f"[REPLY] Successfully sent response to Teams!")
        else:
            print(f"[REPLY] Error: {resp.text}")

    except Exception as err:
        print(f"[ERROR] Failed to send reply: {err}")

    return ("", 200)


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint.

    Returns:
        JSON with status "healthy"
    """
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    print("[INIT] Starting Bot Service on http://0.0.0.0:3978")
    app.run(host="0.0.0.0", port=3978, debug=False)

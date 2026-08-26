import os
import json
import asyncio
import requests
import aiohttp
import base64
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext
from botbuilder.schema import Activity, ActivityTypes

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


def decode_jwt(token: str):
    """Decode JWT token and extract claims."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        return claims
    except Exception as err:
        print(f"[ERROR] Failed to decode JWT: {err}")
        return None


def extract_user_metadata(activity_data: dict, auth_header: str):
    """Extract all available user metadata from Teams."""
    aad_object_id = activity_data.get("from", {}).get("aadObjectId")

    metadata = {
        "from_activity": activity_data.get("from", {}),
        "aad_object_id": aad_object_id,
        "channel_data": activity_data.get("channelData", {})
    }

    # Decode Teams JWT token - contains email, name, and other Azure AD claims
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        jwt_claims = decode_jwt(token)
        if jwt_claims:
            metadata["jwt_claims"] = jwt_claims
            print(f"[USER] ========== USER INFORMATION FROM TEAMS JWT TOKEN ==========")
            print(f"[USER]   Name: {jwt_claims.get('name', 'N/A')}")
            print(f"[USER]   Email: {jwt_claims.get('email', jwt_claims.get('upn', 'N/A'))}")
            print(f"[USER]   Unique ID: {jwt_claims.get('unique_name', 'N/A')}")
            print(f"[USER]   AAD Object ID: {jwt_claims.get('oid', aad_object_id)}")
            print(f"[USER] All Available Claims:")
            for key, value in sorted(jwt_claims.items()):
                if key not in ['aud', 'iss', 'nbf', 'exp', 'iat', 'aio', 'aioo', 'x5c']:  # Skip noise
                    print(f"[USER]   {key}: {value}")
            print(f"[USER] =========================================================")

    return metadata


def get_access_token_manual():
    """Manually get an access token from Azure AD."""
    try:
        url = "https://login.microsoftonline.com/b8087dcf-2a79-43d4-8910-7881a057356a/oauth2/v2.0/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": BOT_APP_ID,
            "client_secret": BOT_APP_PASSWORD,
            "scope": "https://api.botframework.com/.default"
        }

        print(f"[TOKEN] Requesting token from Azure AD...")
        response = requests.post(url, data=data, timeout=10)

        print(f"[TOKEN] Response status: {response.status_code}")

        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"[ERROR] Azure AD rejected credentials")
            return None

    except Exception as err:
        print(f"[ERROR] Failed to get token: {err}")
        return None


def get_graph_access_token():
    """Get access token for Microsoft Graph API."""
    try:
        url = "https://login.microsoftonline.com/b8087dcf-2a79-43d4-8910-7881a057356a/oauth2/v2.0/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": BOT_APP_ID,
            "client_secret": BOT_APP_PASSWORD,
            "scope": "https://graph.microsoft.com/.default"
        }

        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"[ERROR] Failed to get Graph token")
            return None

    except Exception as err:
        print(f"[ERROR] Failed to get Graph token: {err}")
        return None


def get_ai_foundry_token():
    """Get access token for Azure AI Foundry API."""
    try:
        url = "https://login.microsoftonline.com/b8087dcf-2a79-43d4-8910-7881a057356a/oauth2/v2.0/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": BOT_APP_ID,
            "client_secret": BOT_APP_PASSWORD,
            "scope": "https://ai.azure.com/.default"
        }

        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"[ERROR] Failed to get AI Foundry token")
            return None

    except Exception as err:
        print(f"[ERROR] Failed to get AI Foundry token: {err}")
        return None


def get_user_info_from_graph(aad_object_id: str):
    """Fetch user info from Microsoft Graph API."""
    try:
        token = get_graph_access_token()
        if not token:
            print(f"[GRAPH] Could not get access token")
            return None

        url = f"https://graph.microsoft.com/v1.0/users/{aad_object_id}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        print(f"[GRAPH] Fetching user info from: {url}")

        response = requests.get(url, headers=headers, timeout=10)

        print(f"[GRAPH] Response status: {response.status_code}")

        if response.status_code == 200:
            user_data = response.json()

            # Extract and return key fields
            user_info = {
                "mail": user_data.get("mail", "N/A"),
                "department": user_data.get("department", "N/A"),
                "jobTitle": user_data.get("jobTitle", "N/A"),
                "officeLocation": user_data.get("officeLocation", "N/A"),
                "mobilePhone": user_data.get("mobilePhone", "N/A"),
                "displayName": user_data.get("displayName", "N/A")
            }

            print(f"[GRAPH] Successfully fetched user info")
            return user_info
        else:
            error_data = response.json()
            error_code = error_data.get("error", {}).get("code", "Unknown")
            error_msg = error_data.get("error", {}).get("message", "Unknown")
            print(f"[GRAPH] Error ({error_code}): {error_msg}")
            print(f"[GRAPH] Note: Graph API permissions may still be propagating. This usually resolves in 5-10 minutes.")
            return None

    except Exception as err:
        print(f"[ERROR] Failed to fetch user info: {err}")
        return None


def call_foundry_agent(user_message: str, user_metadata: dict) -> tuple:
    """Call the Foundry agent endpoint with the user message. Returns (response_text, metadata)."""
    try:
        token = get_ai_foundry_token()
        if not token:
            print(f"[FOUNDRY] Could not get access token")
            return ("Error: Could not authenticate with Foundry agent", {})

        # Foundry agent endpoint for Responses protocol
        agent_url = "https://aifoundry6449.services.ai.azure.com/api/projects/project6449/agents/super-fun-coding-learn-agent/endpoint/protocols/openai/responses?api-version=v1"

        # Format the request following OpenAI ChatCompletion format
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "input": user_message,
            "stream": False
        }

        print(f"[FOUNDRY] Calling agent at: {agent_url}")
        response = requests.post(agent_url, json=payload, headers=headers, timeout=30)

        print(f"[FOUNDRY] Response status: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print(f"[FOUNDRY] Response type: {type(result)}")

            # Extract metadata from the full response
            agent_response = "No response"
            metadata = {
                "model": result.get("model", "unknown"),
                "agent_name": "unknown",
                "agent_version": "unknown",
                "input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 0,
                "created_at": result.get("created_at", 0),
                "completed_at": result.get("completed_at", 0),
                "processing_time_seconds": 0,
                "response_id": result.get("id", "unknown"),
            }

            # Extract agent reference
            if "agent_reference" in result:
                metadata["agent_name"] = result["agent_reference"].get("name", "unknown")
                metadata["agent_version"] = result["agent_reference"].get("version", "unknown")

            # Extract token usage
            if "usage" in result:
                usage = result["usage"]
                metadata["input_tokens"] = usage.get("input_tokens", 0)
                metadata["output_tokens"] = usage.get("output_tokens", 0)
                metadata["total_tokens"] = usage.get("total_tokens", 0)
                # Extract reasoning tokens if available
                if "output_tokens_details" in usage:
                    metadata["reasoning_tokens"] = usage["output_tokens_details"].get("reasoning_tokens", 0)

            # Calculate processing time
            if metadata["created_at"] and metadata["completed_at"]:
                metadata["processing_time_seconds"] = metadata["completed_at"] - metadata["created_at"]

            # Extract message content from output array
            if "output" in result and isinstance(result["output"], list):
                for item in result["output"]:
                    if item.get("type") == "message" and "content" in item:
                        content = item.get("content", [])
                        if len(content) > 0 and "text" in content[0]:
                            agent_response = content[0]["text"]
                            break

            if agent_response == "No response":
                print(f"[FOUNDRY] Could not extract message content from response")
                agent_response = "No response received"

            print(f"[FOUNDRY] Successfully got response from agent")
            print(f"[FOUNDRY] Tokens - Input: {metadata['input_tokens']}, Output: {metadata['output_tokens']}, Total: {metadata['total_tokens']}")
            return (agent_response, metadata)
        else:
            error_msg = response.text
            print(f"[FOUNDRY] Error ({response.status_code}): {error_msg}")
            return (f"Error: Agent returned status {response.status_code}", {})

    except Exception as err:
        print(f"[ERROR] Failed to call Foundry agent: {err}")
        return (f"Error: {str(err)}", {})


async def on_message_activity(turn_context: TurnContext):
    """Handle incoming messages from Teams (deprecated - using sync endpoint now)."""
    pass


async def on_turn(turn_context: TurnContext):
    """Main turn handler (deprecated - using sync endpoint now)."""
    pass


@app.route("/api/messages", methods=["POST"])
def messages():
    """Bot Framework message endpoint."""
    print(f"[MESSAGE] Received POST to /api/messages")

    if "application/json" in request.headers.get("Content-Type", ""):
        body = request.get_json()
    else:
        return ("Unsupported Media Type", 415)

    user_name = body.get("from", {}).get("name")
    print(f"[MESSAGE] User: {user_name}")

    auth_header = request.headers.get("Authorization", "")

    # Extract metadata
    metadata = extract_user_metadata(body, auth_header)

    # Build response with all available user info
    user_from = metadata.get("from_activity", {})
    aad_object_id = metadata.get("aad_object_id", "N/A")

    # Fetch Graph user info if we have AAD Object ID
    graph_user_info = {}
    if aad_object_id != "N/A":
        graph_user_info = get_user_info_from_graph(aad_object_id) or {}

    # Build user metadata for Foundry agent
    user_metadata = {
        "name": user_from.get('name', 'N/A'),
        "email": graph_user_info.get('mail', 'N/A'),
        "department": graph_user_info.get('department', 'N/A'),
        "job_title": graph_user_info.get('jobTitle', 'N/A'),
        "office_location": graph_user_info.get('officeLocation', 'N/A'),
        "mobile_phone": graph_user_info.get('mobilePhone', 'N/A')
    }

    # Call Foundry agent with the user message
    user_message = body.get('text', '')
    print(f"[MESSAGE] Calling Foundry agent with message: {user_message}")
    agent_response, agent_metadata = call_foundry_agent(user_message, user_metadata)

    # Build response in the requested format
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

    # Get token for response
    token = get_access_token_manual()

    if not token:
        print(f"[ERROR] Could not get access token")
        return ("", 200)

    # Send response to Teams
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

        import requests as req
        resp = req.post(url, json=reply_activity, headers=headers, timeout=10)

        print(f"[REPLY] Response status: {resp.status_code}")
        if resp.status_code == 200 or resp.status_code == 201:
            print(f"[REPLY] Successfully sent with user info!")
        else:
            print(f"[REPLY] Error: {resp.text}")

    except Exception as err:
        print(f"[ERROR] Failed to send reply: {err}")

    return ("", 200)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3978, debug=False)

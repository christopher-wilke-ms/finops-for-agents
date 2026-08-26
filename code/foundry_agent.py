"""
Microsoft Foundry agent integration and API calls.

This module handles:
- Calling Foundry agents via OpenAI-compatible endpoint
- Parsing agent responses and extracting metadata
- Error handling for agent failures
"""

import requests
from typing import Tuple, Dict, Any, Optional
from utils import get_foundry_token

FOUNDRY_ENDPOINT = "https://aifoundry6449.services.ai.azure.com/api/projects/project6449/agents/super-fun-coding-learn-agent/endpoint/protocols/openai/responses?api-version=v1"


def call_foundry_agent(user_message: str, user_metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Call the Foundry agent and retrieve response with metadata.

    Sends a user message to the Foundry agent and extracts:
    - Agent response text
    - Model used
    - Token usage (input, output, reasoning)
    - Processing timestamps
    - Agent version

    Args:
        user_message: User query to send to the agent
        user_metadata: User context dictionary (enriched from Teams + Graph)

    Returns:
        Tuple of (response_text, metadata_dict)
        - response_text: Agent's response message
        - metadata_dict: Token usage, timestamps, model info for FinOps tracking

    Note:
        Requires "Foundry Agent Consumer" RBAC role on the Foundry project
    """
    try:
        token = get_foundry_token()
        if not token:
            print(f"[FOUNDRY] Could not get access token")
            return ("Error: Could not authenticate with Foundry agent", {})

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "input": user_message,
            "stream": False
        }

        print(f"[FOUNDRY] Calling agent at: {FOUNDRY_ENDPOINT}")
        response = requests.post(FOUNDRY_ENDPOINT, json=payload, headers=headers, timeout=30)

        print(f"[FOUNDRY] Response status: {response.status_code}")

        if response.status_code in [200, 201]:
            result = response.json()
            return _parse_foundry_response(result)
        else:
            error_msg = response.text
            print(f"[FOUNDRY] Error ({response.status_code}): {error_msg}")
            return (f"Error: Agent returned status {response.status_code}", {})

    except Exception as err:
        print(f"[ERROR] Failed to call Foundry agent: {err}")
        return (f"Error: {str(err)}", {})


def _parse_foundry_response(response_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Parse Foundry agent response and extract metrics for FinOps tracking.

    Extracts:
    - Agent response text from output array
    - Token usage (input, output, reasoning)
    - Model and agent metadata
    - Processing timestamps
    - Request ID for tracing

    Args:
        response_data: Raw JSON response from Foundry API

    Returns:
        Tuple of (response_text, metadata_dict)

    Internal function - called by call_foundry_agent()
    """
    agent_response = "No response"
    metadata = {
        "model": response_data.get("model", "unknown"),
        "agent_name": "unknown",
        "agent_version": "unknown",
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "created_at": response_data.get("created_at", 0),
        "completed_at": response_data.get("completed_at", 0),
        "processing_time_seconds": 0,
        "response_id": response_data.get("id", "unknown"),
    }

    # Extract agent reference (name and version)
    if "agent_reference" in response_data:
        metadata["agent_name"] = response_data["agent_reference"].get("name", "unknown")
        metadata["agent_version"] = response_data["agent_reference"].get("version", "unknown")

    # Extract token usage
    if "usage" in response_data:
        usage = response_data["usage"]
        metadata["input_tokens"] = usage.get("input_tokens", 0)
        metadata["output_tokens"] = usage.get("output_tokens", 0)
        metadata["total_tokens"] = usage.get("total_tokens", 0)

        # Extract reasoning tokens if available (o1/o1-mini models)
        if "output_tokens_details" in usage:
            metadata["reasoning_tokens"] = usage["output_tokens_details"].get("reasoning_tokens", 0)

    # Calculate processing time from timestamps
    if metadata["created_at"] and metadata["completed_at"]:
        metadata["processing_time_seconds"] = metadata["completed_at"] - metadata["created_at"]

    # Extract message content from output array
    if "output" in response_data and isinstance(response_data["output"], list):
        for item in response_data["output"]:
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

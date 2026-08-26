"""
Utility functions for JWT decoding and token management.

This module provides helper functions for:
- JWT token decoding and claims extraction
- Azure AD token acquisition via client credentials flow
"""

import json
import base64
import requests
import os
from typing import Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()

BOT_APP_ID = os.getenv("BOT_APP_ID")
BOT_APP_PASSWORD = os.getenv("BOT_APP_PASSWORD")
TENANT_ID = "b8087dcf-2a79-43d4-8910-7881a057356a"


def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token and extract claims without verification.

    Args:
        token: JWT token string (format: header.payload.signature)

    Returns:
        Dictionary of decoded claims, or None if decoding fails

    Raises:
        None (returns None on error)
    """
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


def get_access_token(scope: str) -> Optional[str]:
    """
    Obtain an access token from Azure AD using client credentials flow.

    Args:
        scope: OAuth 2.0 scope (e.g., "https://api.botframework.com/.default")

    Returns:
        Access token string, or None if authentication fails
    """
    try:
        url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": BOT_APP_ID,
            "client_secret": BOT_APP_PASSWORD,
            "scope": scope
        }

        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"[ERROR] Azure AD rejected credentials: {response.status_code}")
            return None

    except Exception as err:
        print(f"[ERROR] Failed to get access token: {err}")
        return None


def get_bot_framework_token() -> Optional[str]:
    """
    Get access token for Azure Bot Framework (reply to Teams).

    Returns:
        Access token for Bot Framework, or None on failure
    """
    return get_access_token("https://api.botframework.com/.default")


def get_graph_api_token() -> Optional[str]:
    """
    Get access token for Microsoft Graph API (user profile data).

    Returns:
        Access token for Graph API, or None on failure
    """
    return get_access_token("https://graph.microsoft.com/.default")


def get_foundry_token() -> Optional[str]:
    """
    Get access token for Azure AI Foundry (agent calls).

    Returns:
        Access token for Foundry, or None on failure
    """
    return get_access_token("https://ai.azure.com/.default")

"""
User metadata extraction and enrichment from Teams and Microsoft Graph API.

This module handles:
- Extracting user information from Teams activity data
- JWT token parsing to get initial claims
- Calling Microsoft Graph API for enriched profile data
"""

import requests
from typing import Dict, Optional, Any
from utils import decode_jwt, get_graph_api_token


def extract_user_metadata_from_activity(activity_data: Dict[str, Any], auth_header: str) -> Dict[str, Any]:
    """
    Extract user identity information from Teams activity and JWT token.

    Extracts:
    - User name and ID from Teams activity
    - AAD Object ID for Graph API lookups
    - JWT claims (email, name, org info)

    Args:
        activity_data: Activity payload from Bot Framework
        auth_header: Authorization header containing JWT token

    Returns:
        Dictionary with extracted user metadata and JWT claims
    """
    aad_object_id = activity_data.get("from", {}).get("aadObjectId")

    metadata = {
        "from_activity": activity_data.get("from", {}),
        "aad_object_id": aad_object_id,
        "channel_data": activity_data.get("channelData", {})
    }

    # Decode Teams JWT token for claims
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
                if key not in ['aud', 'iss', 'nbf', 'exp', 'iat', 'aio', 'aioo', 'x5c']:
                    print(f"[USER]   {key}: {value}")
            print(f"[USER] =========================================================")

    return metadata


def get_user_info_from_graph(aad_object_id: str) -> Optional[Dict[str, str]]:
    """
    Fetch enriched user profile data from Microsoft Graph API.

    Retrieves:
    - Email address (mail)
    - Department
    - Job title
    - Office location
    - Mobile phone number
    - Display name

    Args:
        aad_object_id: Azure AD Object ID of the user

    Returns:
        Dictionary with user profile fields, or None on failure

    Note:
        Requires Directory.Read.All and User.Read.All Application permissions
        in Azure AD app registration.
    """
    try:
        token = get_graph_api_token()
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
            print(f"[GRAPH] Note: Graph API permissions may still be propagating (5-10 minutes).")
            return None

    except Exception as err:
        print(f"[ERROR] Failed to fetch user info: {err}")
        return None


def build_user_metadata_dict(activity_from: Dict[str, Any], graph_info: Dict[str, str]) -> Dict[str, str]:
    """
    Build a consolidated user metadata dictionary for agent context.

    Combines information from Teams activity and Graph API into a single
    structured dictionary for passing to the Foundry agent.

    Args:
        activity_from: "from" field of Teams activity
        graph_info: User profile data from Graph API

    Returns:
        Dictionary with consolidated user metadata
    """
    return {
        "name": activity_from.get('name', 'N/A'),
        "email": graph_info.get('mail', 'N/A') if graph_info else 'N/A',
        "department": graph_info.get('department', 'N/A') if graph_info else 'N/A',
        "job_title": graph_info.get('jobTitle', 'N/A') if graph_info else 'N/A',
        "office_location": graph_info.get('officeLocation', 'N/A') if graph_info else 'N/A',
        "mobile_phone": graph_info.get('mobilePhone', 'N/A') if graph_info else 'N/A'
    }

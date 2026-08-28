import logging
import base64
import json
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List
from io import BytesIO

import azure.functions as func
from mcp.types import ImageContent, TextContent, ContentBlock, ResourceLink, CallToolResult
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

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

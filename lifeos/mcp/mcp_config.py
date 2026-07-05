"""MCP configuration center: holds base URLs and helper to build headers.
Never hardcode credentials; use environment variables and OAuth flow.
"""
from __future__ import annotations
import os
from typing import Mapping

class MCPConfig:
    def __init__(self):
        self.calendar_base = os.getenv("CALENDAR_MCP_BASE", "https://calendarmcp.googleapis.com/mcp/v1")
        self.gmail_base = os.getenv("GMAIL_MCP_BASE", "https://gmailmcp.googleapis.com/mcp/v1")

    def auth_headers(self, access_token: str | None = None) -> Mapping[str, str]:
        token = access_token or os.getenv("LIFEOS_OAUTH_TOKEN")
        if not token:
            return {"Content-Type": "application/json"}
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

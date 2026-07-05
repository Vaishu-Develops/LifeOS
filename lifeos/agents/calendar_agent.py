"""Calendar Agent stub — interfaces with Google Calendar MCP.
Includes security checks and uses environment-configured MCP base URL.
"""
from __future__ import annotations
import os
from dotenv import load_dotenv

from lifeos.security.pii_redactor import redact
from lifeos.security.audit_logger import AuditLogger

load_dotenv()
AUDIT = AuditLogger()
MCP_BASE = os.getenv("CALENDAR_MCP_BASE", "https://calendarmcp.googleapis.com/mcp/v1")

class CalendarAgent:
    """Stub for calendar operations: create/read/update/delete events.
    Real implementation should use google-adk tools and OAuth credentials.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.audit = AUDIT

    def list_today(self) -> list[dict]:
        self.audit.log(self.user_id, "calendar.list_today", {})
        # TODO: call MCP using authorized session
        return []

    def create_event(self, event: dict) -> dict:
        self.audit.log(self.user_id, "calendar.create_event", {"event": redact(str(event))})
        # TODO: call MCP create endpoint
        return {"status": "created", "event": event}

Calendar = CalendarAgent

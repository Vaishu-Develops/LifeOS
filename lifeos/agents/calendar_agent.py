"""Calendar Agent — real Google Calendar API integration.
Includes security checks, OAuth credential handling, and direct API calls.
"""
from __future__ import annotations
import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

try:
    from googleapiclient.discovery import build
except ImportError:
    build = None  # type: ignore

from lifeos.security.pii_redactor import redact
from lifeos.security.audit_logger import AuditLogger

load_dotenv()
AUDIT = AuditLogger()
logger = logging.getLogger(__name__)


class CalendarAgent:
    """Google Calendar client: list, create, update, delete events.

    Requires OAuth credentials with calendar.events scope. Methods gracefully
    degrade if google-api-python-client is unavailable or if credentials are None.
    """

    def __init__(self, user_id: str, credentials: Optional[object] = None):
        self.user_id = user_id
        self.audit = AUDIT
        self.credentials = credentials
        self.service = None
        if build and credentials:
            try:
                self.service = build("calendar", "v3", credentials=credentials)
            except Exception as e:
                logger.error("Failed to build Calendar service: %s", e)

    def list_today(self, calendar_id: str = "primary") -> list[dict]:
        """List all events for today on the specified calendar."""
        self.audit.log(self.user_id, "calendar.list_today", {"calendar_id": calendar_id})

        if not self.service:
            logger.warning("No Calendar service available; returning empty events")
            return []

        try:
            today = datetime.utcnow().date().isoformat()
            time_min = f"{today}T00:00:00Z"
            time_max = f"{today}T23:59:59Z"
            
            events_result = self.service.events().list(
                calendarId=calendar_id, 
                timeMin=time_min, 
                timeMax=time_max, 
                singleEvents=True, 
                orderBy='startTime'
            ).execute()
            
            events = events_result.get("items", [])
            
            # Format nicely for the orchestrator
            formatted = []
            for event in events:
                start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
                formatted.append(f"{start}: {event.get('summary', 'Busy')}")
                
            self.audit.log(self.user_id, "calendar.list_today_success", {"count": len(events)})
            return formatted
        except Exception as e:
            logger.error("list_today failed: %s", e)
            self.audit.log(self.user_id, "calendar.list_today_error", {"error": redact(str(e))})
            return []

    def list_week(self, calendar_id: str = "primary") -> list[dict]:
        """List all events for this week."""
        self.audit.log(self.user_id, "calendar.list_week", {"calendar_id": calendar_id})

        if not self.service:
            return []

        try:
            today = datetime.utcnow().date()
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)

            time_min = f"{monday.isoformat()}T00:00:00Z"
            time_max = f"{sunday.isoformat()}T23:59:59Z"

            events_result = self.service.events().list(
                calendarId=calendar_id, 
                timeMin=time_min, 
                timeMax=time_max, 
                singleEvents=True, 
                orderBy='startTime'
            ).execute()
            
            events = events_result.get("items", [])
            self.audit.log(self.user_id, "calendar.list_week_success", {"count": len(events)})
            return events
        except Exception as e:
            logger.error("list_week failed: %s", e)
            self.audit.log(self.user_id, "calendar.list_week_error", {"error": redact(str(e))})
            return []

    def create_event(self, event: dict, calendar_id: str = "primary") -> Optional[dict]:
        """Create a new calendar event."""
        self.audit.log(self.user_id, "calendar.create_event", {"event": redact(str(event))})

        if not self.service:
            return None

        try:
            created = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            self.audit.log(self.user_id, "calendar.create_event_success", {"event_id": created.get("id")})
            return created
        except Exception as e:
            logger.error("create_event failed: %s", e)
            self.audit.log(self.user_id, "calendar.create_event_error", {"error": redact(str(e))})
            return None


Calendar = CalendarAgent

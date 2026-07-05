"""Calendar Agent — real Google Calendar MCP integration.
Includes security checks, OAuth credential handling, and HTTP calls to MCP endpoints.
"""
from __future__ import annotations
import os
import json
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from lifeos.security.pii_redactor import redact
from lifeos.security.audit_logger import AuditLogger
from lifeos.mcp.mcp_config import MCPConfig

load_dotenv()
AUDIT = AuditLogger()
logger = logging.getLogger(__name__)


class CalendarAgent:
    """Google Calendar MCP client: list, create, update, delete events.

    Requires OAuth credentials with calendar.events scope. Methods gracefully
    degrade if requests library is unavailable or if credentials are None.
    """

    def __init__(self, user_id: str, credentials: Optional[object] = None):
        self.user_id = user_id
        self.audit = AUDIT
        self.config = MCPConfig()
        self.credentials = credentials

    def _get_headers(self) -> dict:
        if self.credentials and hasattr(self.credentials, "token"):
            token = self.credentials.token
            return self.config.auth_headers(access_token=token)
        return self.config.auth_headers()

    def list_today(self, calendar_id: str = "primary") -> list[dict]:
        """List all events for today on the specified calendar.

        Args:
            calendar_id: calendar identifier (default: 'primary')
        Returns:
            list of event dicts
        """
        self.audit.log(self.user_id, "calendar.list_today", {"calendar_id": calendar_id})

        if requests is None:
            logger.warning("requests not installed; returning empty events")
            return []

        if self.credentials is None:
            logger.warning("No OAuth credentials available; returning empty events")
            return []

        try:
            today = datetime.utcnow().date().isoformat()
            url = f"{self.config.calendar_base}/calendars/{calendar_id}/events"
            params = {
                "timeMin": f"{today}T00:00:00Z",
                "timeMax": f"{today}T23:59:59Z",
                "singleEvents": True,
                "orderBy": "startTime",
            }
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            events = data.get("items", [])
            self.audit.log(self.user_id, "calendar.list_today_success", {"count": len(events)})
            return events
        except Exception as e:
            logger.error("list_today failed: %s", e)
            self.audit.log(self.user_id, "calendar.list_today_error", {"error": redact(str(e))})
            return []

    def list_week(self, calendar_id: str = "primary") -> list[dict]:
        """List all events for this week.

        Args:
            calendar_id: calendar identifier (default: 'primary')
        Returns:
            list of event dicts
        """
        self.audit.log(self.user_id, "calendar.list_week", {"calendar_id": calendar_id})

        if requests is None or self.credentials is None:
            return []

        try:
            today = datetime.utcnow().date()
            # Find Monday of this week
            monday = today - timedelta(days=today.weekday())
            # Find Sunday
            sunday = monday + timedelta(days=6)

            url = f"{self.config.calendar_base}/calendars/{calendar_id}/events"
            params = {
                "timeMin": f"{monday.isoformat()}T00:00:00Z",
                "timeMax": f"{sunday.isoformat()}T23:59:59Z",
                "singleEvents": True,
                "orderBy": "startTime",
            }
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            events = data.get("items", [])
            self.audit.log(self.user_id, "calendar.list_week_success", {"count": len(events)})
            return events
        except Exception as e:
            logger.error("list_week failed: %s", e)
            self.audit.log(self.user_id, "calendar.list_week_error", {"error": redact(str(e))})
            return []

    def create_event(self, event: dict, calendar_id: str = "primary") -> Optional[dict]:
        """Create a new calendar event.

        Args:
            event: dict with keys like 'summary', 'start', 'end', 'description'
            calendar_id: calendar identifier (default: 'primary')
        Returns:
            created event dict or None on error
        """
        self.audit.log(self.user_id, "calendar.create_event", {"event": redact(str(event))})

        if requests is None or self.credentials is None:
            return None

        try:
            url = f"{self.config.calendar_base}/calendars/{calendar_id}/events"
            resp = requests.post(
                url,
                headers=self._get_headers(),
                json=event,
                timeout=10,
            )
            resp.raise_for_status()
            created = resp.json()
            self.audit.log(self.user_id, "calendar.create_event_success", {"event_id": created.get("id")})
            return created
        except Exception as e:
            logger.error("create_event failed: %s", e)
            self.audit.log(self.user_id, "calendar.create_event_error", {"error": redact(str(e))})
            return None

    def find_free_slots(self, duration_minutes: int = 30, calendar_id: str = "primary") -> list[dict]:
        """Find available time slots today.

        Simple implementation: identifies gaps in today's schedule larger than duration_minutes.
        Args:
            duration_minutes: minimum slot size (default: 30)
            calendar_id: calendar identifier (default: 'primary')
        Returns:
            list of dicts with 'start' and 'end' times
        """
        self.audit.log(self.user_id, "calendar.find_free_slots", {"duration_minutes": duration_minutes})

        events = self.list_today(calendar_id)
        if not events:
            today = datetime.utcnow().date()
            return [{"start": f"{today}T09:00:00Z", "end": f"{today}T17:00:00Z"}]

        # Sort events by start time
        events = sorted(events, key=lambda e: e.get("start", {}).get("dateTime", ""))

        slots = []
        day_start = datetime.utcnow().replace(hour=9, minute=0, second=0)
        day_end = datetime.utcnow().replace(hour=17, minute=0, second=0)

        current = day_start
        for event in events:
            event_start = event.get("start", {}).get("dateTime")
            event_end = event.get("end", {}).get("dateTime")
            if event_start:
                # Gap between current and event start
                gap_minutes = int((datetime.fromisoformat(event_start) - current).total_seconds() / 60)
                if gap_minutes >= duration_minutes:
                    slots.append({"start": current.isoformat(), "end": event_start})
                current = datetime.fromisoformat(event_end)

        # Gap from current to day end
        gap_minutes = int((day_end - current).total_seconds() / 60)
        if gap_minutes >= duration_minutes:
            slots.append({"start": current.isoformat(), "end": day_end.isoformat()})

        return slots


# Need timedelta for list_week
from datetime import timedelta

Calendar = CalendarAgent

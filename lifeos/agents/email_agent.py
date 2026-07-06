"""Email Agent — real Gmail API integration.
Includes security checks, OAuth credential handling, and direct API calls.
"""
from __future__ import annotations
import os
import logging
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


class EmailAgent:
    """Gmail API client: search, read, and draft messages."""

    def __init__(self, user_id: str, credentials: Optional[object] = None):
        self.user_id = user_id
        self.audit = AUDIT
        self.credentials = credentials
        self.service = None
        if build and credentials:
            try:
                self.service = build("gmail", "v1", credentials=credentials)
            except Exception as e:
                logger.error("Failed to build Gmail service: %s", e)

    def search_threads(self, query: str = "", max_results: int = 10) -> list[dict]:
        """Search for email threads matching a query."""
        self.audit.log(self.user_id, "email.search", {"query": redact(query), "max_results": max_results})

        if not self.service:
            logger.warning("No Gmail service available; returning empty threads")
            return []

        try:
            q = query or "is:unread"
            resp = self.service.users().threads().list(userId='me', q=q, maxResults=max_results).execute()
            threads = resp.get("threads", [])
            self.audit.log(self.user_id, "email.search_success", {"count": len(threads)})
            return threads
        except Exception as e:
            logger.error("search_threads failed: %s", e)
            self.audit.log(self.user_id, "email.search_error", {"error": redact(str(e))})
            return []

    def get_thread(self, thread_id: str) -> Optional[dict]:
        """Fetch a single thread with all messages."""
        self.audit.log(self.user_id, "email.get_thread", {"thread_id": redact(thread_id)})

        if not self.service:
            return None

        try:
            thread = self.service.users().threads().get(userId='me', id=thread_id).execute()
            self.audit.log(self.user_id, "email.get_thread_success", {"thread_id": redact(thread_id)})
            return thread
        except Exception as e:
            logger.error("get_thread failed: %s", e)
            self.audit.log(self.user_id, "email.get_thread_error", {"error": redact(str(e))})
            return None

    def draft_reply(self, thread_id: str, body: str) -> Optional[dict]:
        """Create a reply draft for a thread."""
        self.audit.log(self.user_id, "email.draft_reply", {"thread_id": redact(thread_id), "body": redact(body)})

        if not self.service:
            return None

        try:
            thread = self.get_thread(thread_id)
            if not thread:
                return None

            subject = "Re: [original subject]"
            if thread.get("messages"):
                headers = thread["messages"][0].get("payload", {}).get("headers", [])
                for h in headers:
                    if h.get("name").lower() == "subject":
                        subject = "Re: " + h.get("value", "")
                        break

            message = {
                "threadId": thread_id,
                "message": {
                    "raw": self._encode_message(to="", subject=subject, body=body)
                }
            }

            draft = self.service.users().drafts().create(userId='me', body=message).execute()
            self.audit.log(self.user_id, "email.draft_reply_success", {"draft_id": draft.get("id")})
            return draft
        except Exception as e:
            logger.error("draft_reply failed: %s", e)
            self.audit.log(self.user_id, "email.draft_reply_error", {"error": redact(str(e))})
            return None

    def _encode_message(self, to: str, subject: str, body: str) -> str:
        """Encode a message for Gmail API (base64url)."""
        import base64
        msg = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        return base64.urlsafe_b64encode(msg.encode()).decode()


Email = EmailAgent

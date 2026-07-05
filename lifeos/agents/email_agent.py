"""Email Agent — real Gmail MCP integration.
Includes security checks, OAuth credential handling, and HTTP calls to MCP endpoints.
"""
from __future__ import annotations
import os
import json
import logging
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


class EmailAgent:
    """Gmail MCP client: search, read, and draft messages.

    Requires OAuth credentials with gmail.readonly and gmail.compose scopes.
    Methods gracefully degrade if requests library is unavailable or if credentials are None.
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

    def search_threads(self, query: str = "", max_results: int = 10) -> list[dict]:
        """Search for email threads matching a query.

        Args:
            query: Gmail search query (e.g., 'from:alice@example.com', 'is:unread')
            max_results: max threads to return (default: 10)
        Returns:
            list of thread dicts with id, messages, subject
        """
        self.audit.log(self.user_id, "email.search", {"query": redact(query), "max_results": max_results})

        if requests is None:
            logger.warning("requests not installed; returning empty threads")
            return []

        if self.credentials is None:
            logger.warning("No OAuth credentials available; returning empty threads")
            return []

        try:
            url = f"{self.config.gmail_base}/users/me/threads"
            params = {
                "q": query or "is:unread",
                "maxResults": max_results,
            }
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            threads = data.get("threads", [])
            self.audit.log(self.user_id, "email.search_success", {"count": len(threads)})
            return threads
        except Exception as e:
            logger.error("search_threads failed: %s", e)
            self.audit.log(self.user_id, "email.search_error", {"error": redact(str(e))})
            return []

    def get_thread(self, thread_id: str) -> Optional[dict]:
        """Fetch a single thread with all messages.

        Args:
            thread_id: Gmail thread ID
        Returns:
            thread dict with messages or None on error
        """
        self.audit.log(self.user_id, "email.get_thread", {"thread_id": redact(thread_id)})

        if requests is None or self.credentials is None:
            return None

        try:
            url = f"{self.config.gmail_base}/users/me/threads/{thread_id}"
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            resp.raise_for_status()
            thread = resp.json()
            self.audit.log(self.user_id, "email.get_thread_success", {"thread_id": redact(thread_id)})
            return thread
        except Exception as e:
            logger.error("get_thread failed: %s", e)
            self.audit.log(self.user_id, "email.get_thread_error", {"error": redact(str(e))})
            return None

    def draft_reply(self, thread_id: str, body: str) -> Optional[dict]:
        """Create a reply draft for a thread.

        Args:
            thread_id: Gmail thread ID
            body: reply message body (plain text or HTML)
        Returns:
            draft dict with draft id or None on error
        """
        self.audit.log(
            self.user_id,
            "email.draft_reply",
            {"thread_id": redact(thread_id), "body": redact(body)},
        )

        if requests is None or self.credentials is None:
            return None

        try:
            # Get the original thread to find the subject
            thread = self.get_thread(thread_id)
            if not thread:
                return None

            # Extract original subject for reply
            subject = "Re: [original subject]"
            if thread.get("messages"):
                headers = thread["messages"][0].get("payload", {}).get("headers", [])
                for h in headers:
                    if h.get("name").lower() == "subject":
                        subject = "Re: " + h.get("value", "")
                        break

            # Build the reply message
            message = {
                "threadId": thread_id,
                "raw": self._encode_message(
                    to="",  # Would be set from thread context in real impl
                    subject=subject,
                    body=body,
                ),
            }

            url = f"{self.config.gmail_base}/users/me/drafts"
            resp = requests.post(url, headers=self._get_headers(), json=message, timeout=10)
            resp.raise_for_status()
            draft = resp.json()
            self.audit.log(self.user_id, "email.draft_reply_success", {"draft_id": draft.get("id")})
            return draft
        except Exception as e:
            logger.error("draft_reply failed: %s", e)
            self.audit.log(self.user_id, "email.draft_reply_error", {"error": redact(str(e))})
            return None

    def _encode_message(self, to: str, subject: str, body: str) -> str:
        """Encode a message for Gmail API (base64url).

        This is a simplified version; production code should use proper email libs.
        """
        import base64

        msg = f"To: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        return base64.urlsafe_b64encode(msg.encode()).decode()


Email = EmailAgent

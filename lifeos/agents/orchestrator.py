"""Orchestrator Agent — simple keyword intent classifier and router.

This minimal orchestrator is intended for local testing and demos: it classifies user text
using lightweight keyword rules, routes to the Task/Calendar/Email agent stubs, and
returns a small structured response. Security: all inputs and payloads are redacted in
audit logs. Replace with a Google ADK LlmAgent-powered classifier for production.
"""
from __future__ import annotations
import os
from typing import Any
from dotenv import load_dotenv

# Security helpers (PII redaction + audit logging)
from lifeos.security.pii_redactor import redact
from lifeos.security.audit_logger import AuditLogger

# Import agent stubs
from lifeos.agents.task_agent import TaskAgent
from lifeos.agents.calendar_agent import CalendarAgent
from lifeos.agents.email_agent import EmailAgent
# ADK client wrapper
from lifeos.agents.adk_wrapper import ADKClient

load_dotenv()
AUDIT = AuditLogger()

class OrchestratorAgent:
    """Minimal orchestrator with ADK intent routing (falls back to deterministic rules).

    Accepts OAuth credentials and passes them to Calendar and Email agents.
    """

    def __init__(self, model: str | None = None, credentials: object | None = None):
        self.model = model or os.getenv("LIFEOS_MODEL", "gemini-2.0-flash")
        self.audit = AUDIT
        # ADK client for intent classification
        self.adk = ADKClient(model=self.model)
        # OAuth credentials to pass to sub-agents
        self.credentials = credentials

    def _classify_intent(self, text: str) -> str:
        # Prefer ADK classification when available; fallback to deterministic rules
        try:
            intent = self.adk.classify_intent(text)
            if intent:
                return intent
        except Exception:
            pass

        t = (text or "").lower()
        # Order matters: more specific rules first
        if any(k in t for k in ["add task", "create task", "new task", "todo"]):
            return "task.add"
        if any(k in t for k in ["list tasks", "show tasks", "my tasks", "what are my tasks"]):
            return "task.list"
        if any(k in t for k in ["draft reply", "reply to", "reply"]):
            return "email.reply"
        if any(k in t for k in ["search email", "find email", "inbox", "unread"]):
            return "email.search"
        if any(k in t for k in ["calendar", "event", "meeting", "schedule", "what does my"]):
            return "calendar.list"
        return "unknown"

    def handle_user(self, user_id: str, text: str) -> dict[str, Any]:
        """Handle user input: classify intent, route to sub-agent, and return structured result.

        Args:
            user_id: opaque user id used for audit logging
            text: raw user text
        Returns:
            dict with keys: intent, route, result (agent-specific)
        """
        safe_text = redact(text)
        self.audit.log(user_id, "orchestrator.receive", {"text": safe_text})

        intent = self._classify_intent(text)
        result: dict[str, Any] = {"intent": intent}

        try:
            if intent == "task.add":
                # Very small heuristic to extract title after 'add' or 'create'
                title = self._extract_after_keywords(text, ["add task", "create task", "add", "new task"]) or text
                task_agent = TaskAgent(user_id)
                task_id = task_agent.add_task(title=title)
                result.update({"route": "task", "action": "add", "task_id": task_id})

            elif intent == "task.list":
                task_agent = TaskAgent(user_id)
                tasks = task_agent.list_tasks()
                result.update({"route": "task", "action": "list", "count": len(tasks), "tasks": tasks})

            elif intent == "email.search":
                query = text
                email_agent = EmailAgent(user_id, credentials=self.credentials)
                threads = email_agent.search_threads(query=query)
                result.update({"route": "email", "action": "search", "count": len(threads), "threads": threads})

            elif intent == "email.reply":
                # naive: expect 'reply to <thread id>: <message>'
                # fallback to drafting an empty reply
                email_agent = EmailAgent(user_id, credentials=self.credentials)
                # Attempt to split by ':' to get body
                parts = text.split(":", 1)
                body = parts[1].strip() if len(parts) > 1 else ""
                # thread id extraction would be ADK-driven; use placeholder
                thread_id = "unknown"
                draft = email_agent.draft_reply(thread_id=thread_id, body=body)
                result.update({"route": "email", "action": "reply", "draft": draft})

            elif intent == "calendar.list":
                cal = CalendarAgent(user_id, credentials=self.credentials)
                events = cal.list_today()
                result.update({"route": "calendar", "action": "list_today", "count": len(events), "events": events})

            else:
                result.update({"route": "none", "message": "Sorry, I didn't understand. Try: add task, list tasks, search email, or show calendar."})

            # Audit the response (redacted)
            self.audit.log(user_id, "orchestrator.respond", {"response": redact(str(result))})
            return result

        except Exception as e:
            # Ensure any exception is logged (redacted) and a safe message is returned
            self.audit.log(user_id, "orchestrator.error", {"error": redact(str(e))})
            return {"intent": intent, "route": "error", "message": "Internal error"}

    def _extract_after_keywords(self, text: str, keywords: list[str]) -> str | None:
        t = text or ""
        lt = t.lower()
        for k in keywords:
            if k in lt:
                idx = lt.find(k)
                after = t[idx + len(k):].strip()
                if after:
                    return after
        return None


# Convenience alias
Orchestrator = OrchestratorAgent

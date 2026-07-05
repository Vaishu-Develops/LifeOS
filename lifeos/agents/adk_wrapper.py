"""ADK client wrapper.

Tries to use google-adk if available; falls back to a lightweight keyword classifier.
This file provides a single ADKClient class with method classify_intent(text) that returns
an intent string understood by the Orchestrator.
"""
from __future__ import annotations
import os
from typing import Optional

try:
    # google-adk API surface may differ; import if available. Real ADK integration
    # should replace the fallback logic below with actual LlmAgent calls.
    import google_adk  # type: ignore
    _HAS_ADK = True
except Exception:
    _HAS_ADK = False

class ADKClient:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("LIFEOS_MODEL", "gemini-2.0-flash")
        self._has_adk = _HAS_ADK
        # placeholder for real agent instance if ADK available
        self._agent = None
        if self._has_adk:
            try:
                # Example: create an LlmAgent if provided by google_adk
                # self._agent = google_adk.LlmAgent(model=self.model)
                self._agent = None  # real initialization goes here
            except Exception:
                self._has_adk = False

    def classify_intent(self, text: str) -> str:
        """Return an intent string (e.g., 'task.add', 'task.list', 'email.search', 'calendar.list').

        If ADK is available, this should call the LLM agent to classify intent. When ADK is
        not available, a deterministic keyword fallback is used so the orchestrator remains
        functional for local demos and tests.
        """
        if self._has_adk and self._agent is not None:
            try:
                # TODO: call the real ADK LlmAgent with a concise prompt to classify intent
                # response = self._agent.predict(prompt)
                # return response.intent
                pass
            except Exception:
                # Fall through to fallback classifier
                pass

        # Fallback deterministic classifier
        t = (text or "").lower()
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

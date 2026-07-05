"""ADK client wrapper.

Tries to use google-adk if available; otherwise falls back to a deterministic classifier.
Provides ADKClient.classify_intent(text) which returns an intent string understood by Orchestrator.

When ADK is available this uses a concise instruction-following prompt that asks the model to
output a JSON object like: {"intent": "task.add", "confidence": 0.95}
Only the "intent" is used by the orchestrator; confidence may be used to fall back.
"""
from __future__ import annotations
import os
import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import google_adk  # type: ignore
    _HAS_ADK = True
except Exception:
    _HAS_ADK = False


class ADKClient:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("LIFEOS_MODEL", "gemini-2.0-flash")
        self._has_adk = _HAS_ADK
        self._agent = None

        if self._has_adk:
            try:
                # Attempt to find a reasonable LLM agent constructor on the google_adk module.
                AgentClass = getattr(google_adk, "LlmAgent", None) or getattr(google_adk, "LLM", None) or getattr(google_adk, "Agent", None)
                if AgentClass is not None:
                    # Many ADK clients accept a model param; adapt if the real API differs.
                    try:
                        self._agent = AgentClass(model=self.model)
                    except TypeError:
                        # Fall back to no-arg construction
                        self._agent = AgentClass()
                else:
                    # If no recognizable agent class is present, disable ADK usage
                    self._has_adk = False
            except Exception as e:
                logger.debug("ADK initialization failed: %s", e)
                self._has_adk = False

    def _build_prompt(self, text: str) -> str:
        # System instruction: be a strict classifier that emits JSON only
        system = (
            "You are an intent classification assistant for LifeOS.\n"
            "Given a single user utterance, return a JSON object with the following fields:\n"
            "- intent: one of [task.add, task.list, email.search, email.reply, calendar.list, unknown]\n"
            "- confidence: floating number between 0 and 1 representing confidence.\n"
            "Respond with ONLY a single valid JSON object and nothing else.\n"
        )
        user = f"User utterance: {text}"
        return system + "\n" + user

    def _call_agent(self, prompt: str) -> Optional[str]:
        # Try several common method names on the agent instance to be compatible with ADK versions
        if not self._has_adk or self._agent is None:
            return None

        for method_name in ("predict", "generate", "complete", "run", "call"):
            method = getattr(self._agent, method_name, None)
            if callable(method):
                try:
                    resp = method(prompt)
                    # Extract text content from common response shapes
                    if isinstance(resp, str):
                        return resp
                    if hasattr(resp, "text"):
                        return getattr(resp, "text")
                    if hasattr(resp, "content"):
                        return getattr(resp, "content")
                    # Fallback to string conversion
                    return str(resp)
                except Exception as e:
                    logger.debug("ADK agent method %s failed: %s", method_name, e)
                    continue
        return None

    def _extract_json(self, text: str) -> Optional[dict]:
        if not text:
            return None
        # Find first JSON object in text
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            # Try to repair common issues (e.g., trailing commas)
            try:
                cleaned = re.sub(r",\s*}", "}", m.group(0))
                return json.loads(cleaned)
            except Exception:
                return None

    def classify_intent(self, text: str) -> str:
        """Return an intent string such as 'task.add' or fallback to deterministic rules.

        If ADK is available, send a concise prompt and parse the JSON response. If the parsed
        response contains an "intent" with confidence >= 0.4, return it; otherwise fall back.
        """
        # Prefer ADK when available
        if self._has_adk and self._agent is not None:
            try:
                prompt = self._build_prompt(text)
                raw = self._call_agent(prompt)
                if raw:
                    obj = self._extract_json(raw)
                    if isinstance(obj, dict):
                        intent = obj.get("intent")
                        try:
                            confidence = float(obj.get("confidence", 0.0))
                        except Exception:
                            confidence = 0.0
                        if intent and confidence >= 0.4:
                            return intent
            except Exception as e:
                logger.debug("ADK classify_intent failed, falling back: %s", e)

        # Deterministic fallback
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

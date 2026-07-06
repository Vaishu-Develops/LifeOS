"""Gemini client wrapper.

Uses the official google-genai library to perform intent classification.
Provides ADKClient.classify_intent(text) which returns an intent string understood by Orchestrator.
"""
from __future__ import annotations
import os
import re
import json
import logging
from typing import Optional

try:
    from google import genai
    _HAS_GEMINI = True
except ImportError:
    _HAS_GEMINI = False

logger = logging.getLogger(__name__)

class ADKClient:
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("LIFEOS_MODEL", "gemini-2.0-flash")
        self._has_gemini = _HAS_GEMINI
        self.client = None
        
        if self._has_gemini:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                try:
                    self.client = genai.Client(api_key=api_key)
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini Client: {e}")
                    self._has_gemini = False
            else:
                logger.warning("GEMINI_API_KEY not found in environment. Falling back to deterministic rules.")
                self._has_gemini = False

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
            try:
                cleaned = re.sub(r",\s*}", "}", m.group(0))
                return json.loads(cleaned)
            except Exception:
                return None

    def classify_intent(self, text: str) -> str:
        """Return an intent string such as 'task.add' or fallback to deterministic rules."""
        if self._has_gemini and self.client:
            try:
                prompt = self._build_prompt(text)
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                raw = response.text
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
                logger.debug("Gemini classify_intent failed, falling back: %s", e)

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

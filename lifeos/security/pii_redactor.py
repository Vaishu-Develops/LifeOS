"""PII redaction utilities — used before any logging or telemetry.
Simple regex-based redactor for emails and phone-like patterns.
"""
from __future__ import annotations
import re

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s-]?)?(\(?\d{3,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}")

def redact(text: str) -> str:
    if not text:
        return text
    t = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    t = PHONE_RE.sub("[REDACTED_PHONE]", t)
    return t

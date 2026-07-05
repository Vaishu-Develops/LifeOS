"""Simple audit logger: records agent actions with timestamp and user id.
Logs are minimal and redact inputs before writing. Meant for local development; replace with secure audit sink in production.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from .pii_redactor import redact

LOG_PATH = Path(__file__).resolve().parents[1] / "database" / "audit.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

class AuditLogger:
    def __init__(self, path: Path | None = None):
        self.path = path or LOG_PATH

    def log(self, user_id: str, action: str, payload: Any | None = None) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": redact(user_id),
            "action": action,
            "payload": redact(json.dumps(payload)) if payload is not None else None,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

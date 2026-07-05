"""Task Agent — SQLite-backed task store.
Includes simple CRUD and ensures DB file is created under package database/.
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

from lifeos.security.pii_redactor import redact
from lifeos.security.audit_logger import AuditLogger

load_dotenv()
AUDIT = AuditLogger()

DB_PATH = os.getenv("LIFEOS_TASK_DB") or str(Path(__file__).resolve().parents[1] / "database" / "tasks.db")

class TaskAgent:
    def __init__(self, user_id: str, db_path: str | None = None):
        self.user_id = user_id
        self.db_path = db_path or DB_PATH
        self.audit = AUDIT
        self._ensure_db()

    def _ensure_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    details TEXT,
                    due_date TEXT,
                    completed INTEGER DEFAULT 0
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add_task(self, title: str, details: str | None = None, due_date: str | None = None) -> int:
        self.audit.log(self.user_id, "task.add", {"title": redact(title)})
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute("INSERT INTO tasks (title, details, due_date) VALUES (?, ?, ?)", (title, details, due_date))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def list_tasks(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        q = "SELECT id, title, details, due_date, completed FROM tasks"
        if not include_completed:
            q += " WHERE completed = 0"
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(q).fetchall()
            return [dict(id=r[0], title=r[1], details=r[2], due_date=r[3], completed=bool(r[4])) for r in rows]
        finally:
            conn.close()

Task = TaskAgent

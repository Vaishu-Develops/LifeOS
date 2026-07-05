"""OAuth helpers for LifeOS MCP integrations.

Provides small helper wrappers around google-auth-oauthlib's InstalledAppFlow and
credential storage. Functions gracefully handle missing libraries for local dev.
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Optional

try:
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    from google.oauth2.credentials import Credentials  # type: ignore
except Exception:  # pragma: no cover - import may fail in minimal env
    InstalledAppFlow = None  # type: ignore
    Credentials = None  # type: ignore

TOKEN_PATH = Path(__file__).resolve().parents[1] / "database" / "tokens.json"
TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)


def build_flow(client_secrets_file: str, scopes: list[str]) -> "InstalledAppFlow":
    if InstalledAppFlow is None:
        raise RuntimeError("google_auth_oauthlib is not installed")
    return InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes=scopes)


def get_authorize_url(flow: "InstalledAppFlow") -> str:
    # For web server flow use flow.authorization_url, for local installed flow use run_local_server
    if InstalledAppFlow is None:
        raise RuntimeError("google_auth_oauthlib is not installed")
    auth_url, _ = flow.authorization_url(prompt="consent")
    return auth_url


def exchange_code(flow: "InstalledAppFlow", code: str) -> "Credentials":
    if InstalledAppFlow is None:
        raise RuntimeError("google_auth_oauthlib is not installed")
    flow.fetch_token(code=code)
    return flow.credentials


def save_tokens(credentials: "Credentials", path: Optional[str] = None) -> None:
    p = Path(path) if path else TOKEN_PATH
    data = {
        "token": credentials.token,
        "refresh_token": getattr(credentials, "refresh_token", None),
        "token_uri": getattr(credentials, "token_uri", None),
        "client_id": getattr(credentials, "client_id", None),
        "client_secret": getattr(credentials, "client_secret", None),
        "scopes": getattr(credentials, "scopes", None),
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_tokens(path: Optional[str] = None) -> Optional["Credentials"]:
    p = Path(path) if path else TOKEN_PATH
    if not p.exists():
        return None
    if Credentials is None:
        raise RuntimeError("google-auth is not installed")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )


def refresh_credentials(credentials: "Credentials") -> "Credentials":
    if Credentials is None:
        raise RuntimeError("google-auth is not installed")
    request = None
    try:
        # Import here to avoid top-level dependency in minimal environments
        from google.auth.transport.requests import Request  # type: ignore
        request = Request()
    except Exception:
        raise RuntimeError("google-auth transport is not available to refresh tokens")
    credentials.refresh(request)
    return credentials

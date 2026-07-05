# LifeOS

LifeOS is a multi-agent personal command center for coordinating calendar, email, and task workflows through a conversational Streamlit UI. The codebase is a working scaffold for the Google ADK-based hackathon submission, with separate modules for orchestration, OAuth, security, and the user interface.

## What’s Included

- Calendar, email, and task agent stubs coordinated by a central orchestrator
- Streamlit chat UI for local interaction
- OAuth helpers for Google API access
- Security utilities for PII redaction and audit logging
- Package layout ready for future agent and database expansion

## Quick Start

1. Create a virtual environment if you do not already have one.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set your Google OAuth credentials.
4. Launch the app with `streamlit run lifeos/ui/app.py`.

## Configuration

Set the following environment variable for OAuth sign-in:

- `LIFEOS_OAUTH_CLIENT_SECRET_FILE`: path to your Google OAuth client secret JSON

Optional local settings:

- `LIFEOS_USER_ID`: overrides the default local user identifier

Tokens are persisted locally in `lifeos/database/tokens.json` when OAuth sign-in succeeds.

## Project Layout

- `lifeos/agents/`: orchestrator and domain agent wrappers
- `lifeos/mcp/`: OAuth and MCP configuration helpers
- `lifeos/security/`: audit logging and PII redaction utilities
- `lifeos/ui/`: Streamlit application entry point
- `lifeos/database/`: local persistence and token storage

## Security Notes

- Credentials are environment-based and should not be committed to source control.
- PII redaction and audit logging are part of the repository’s security scaffolding.
- OAuth tokens are stored locally for reuse and refresh during development.

## Development Notes

This repository is intentionally lightweight and focused on scaffolding. The UI can be run locally without additional services, while agent behavior and backend integrations can be extended module by module.

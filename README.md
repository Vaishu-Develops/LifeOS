# LifeOS — Multi-Agent Personal Command Center

LifeOS is a multi-agent personal command center that unifies calendar, email, and task workflows behind a conversational UI. This repository contains stubs and scaffolding for the Google ADK-based agents used in the Kaggle Hackathon submission.

Quick start (local):
1. Copy .env.example to .env and set OAuth credentials.
2. pip install -r requirements.txt
3. streamlit run lifeos/ui/app.py

Project layout mirrors the hackathon plan: agents/, mcp/, security/, ui/, database/.
Security: PII redaction, audit logs, and environment-based credentials.

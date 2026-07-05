"""Streamlit chat UI for LifeOS — wired to Orchestrator with OAuth sign-in.
Run locally with: streamlit run lifeos/ui/app.py

To use OAuth flows:
1. Set LIFEOS_OAUTH_CLIENT_SECRET_FILE env var to path of Google OAuth credentials JSON.
2. LifeOS will store/refresh tokens in lifeos/database/tokens.json.
"""
from __future__ import annotations
import os
import streamlit as st
from dotenv import load_dotenv

# Import the orchestrator and oauth helpers
from lifeos.agents.orchestrator import Orchestrator
from lifeos.mcp import oauth

load_dotenv()

st.set_page_config(page_title="LifeOS — Personal Command Center", layout="wide")
st.title("LifeOS")
st.write("Your AI-powered personal command center")

if "history" not in st.session_state:
    st.session_state.history = []
if "credentials" not in st.session_state:
    st.session_state.credentials = None

USER_ID = os.getenv("LIFEOS_USER_ID", "local_user")

# Instantiate orchestrator once per session, or recreate if credentials changed
if "orchestrator" not in st.session_state or "last_creds_state" not in st.session_state:
    st.session_state.orchestrator = Orchestrator(credentials=st.session_state.credentials)
    st.session_state.last_creds_state = st.session_state.credentials
elif st.session_state.last_creds_state is not st.session_state.credentials:
    # Credentials changed, recreate orchestrator with new creds
    st.session_state.orchestrator = Orchestrator(credentials=st.session_state.credentials)
    st.session_state.last_creds_state = st.session_state.credentials

# ============================================================================
# Auth Sidebar
# ============================================================================
with st.sidebar:
    st.subheader("Authentication")
    auth_status = st.session_state.credentials is not None
    if auth_status:
        st.success("✓ OAuth Authorized")
        if st.button("Sign Out"):
            st.session_state.credentials = None
            st.rerun()
    else:
        st.warning("Not authorized for Calendar/Gmail")
        if st.button("Sign In with Google"):
            # Try to load persisted tokens first
            try:
                creds = oauth.load_tokens()
                if creds and creds.valid:
                    st.session_state.credentials = creds
                    st.success("Credentials loaded from storage!")
                    st.rerun()
                elif creds and creds.expired and creds.refresh_token:
                    # Token expired but can refresh
                    creds = oauth.refresh_credentials(creds)
                    oauth.save_tokens(creds)
                    st.session_state.credentials = creds
                    st.success("Credentials refreshed!")
                    st.rerun()
            except Exception as e:
                st.error(f"OAuth error: {e}")
                st.info("Ensure LIFEOS_OAUTH_CLIENT_SECRET_FILE is set in .env")

# ============================================================================
# Chat Interface
# ============================================================================
st.subheader("Chat")
with st.form("input_form", clear_on_submit=True):
    user_input = st.text_input("Ask LifeOS something:")
    col1, col2 = st.columns(2)
    with col1:
        submitted = st.form_submit_button("Send")

if submitted and user_input:
    st.session_state.history.append({"user": user_input})
    orchestrator = st.session_state.orchestrator
    result = orchestrator.handle_user(USER_ID, user_input)
    assistant_msg = result.get("message") or result.get("summary") or None
    if not assistant_msg:
        parts = [f"intent: {result.get('intent', 'unknown')}", f"route: {result.get('route', 'none')}"]
        if result.get("action"):
            parts.append(f"action: {result['action']}")
        if result.get("task_id"):
            parts.append(f"task_id: {result['task_id']}")
        assistant_msg = " | ".join(parts)
    st.session_state.history.append({"assistant": assistant_msg})

for msg in st.session_state.history:
    if "user" in msg:
        st.chat_message("user").write(msg["user"])
    else:
        st.chat_message("assistant").write(msg["assistant"])


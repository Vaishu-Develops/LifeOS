"""Streamlit chat UI for LifeOS — wired to the minimal Orchestrator.
Run locally with: streamlit run lifeos/ui/app.py
"""
from __future__ import annotations
import os
import streamlit as st
from dotenv import load_dotenv

# Import the orchestrator implemented in agents
from lifeos.agents.orchestrator import Orchestrator

load_dotenv()

st.set_page_config(page_title="LifeOS — Personal Command Center")
st.title("LifeOS")
st.write("Your AI-powered personal command center")

if "history" not in st.session_state:
    st.session_state.history = []

# Simple user id for local demos
USER_ID = os.getenv("LIFEOS_USER_ID", "local_user")

# Instantiate orchestrator once per session
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = Orchestrator()

with st.form("input_form", clear_on_submit=True):
    user_input = st.text_input("Ask LifeOS something:")
    submitted = st.form_submit_button("Send")

if submitted and user_input:
    st.session_state.history.append({"user": user_input})
    # Call orchestrator to handle the input (synchronous, quick)
    orchestrator = st.session_state.orchestrator
    result = orchestrator.handle_user(USER_ID, user_input)
    # Prefer a friendly assistant message; fall back to raw result
    assistant_msg = result.get("message") or result.get("summary") or None
    if not assistant_msg:
        # Build a concise summary for display
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

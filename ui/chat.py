"""Streamlit Chat UI for the Enterprise RAG system."""

import json
import requests
import streamlit as st

# ── Configuration ────────────────────────────────────────────────────
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Enterprise RAG Assistant",
    page_icon="🏢",
    layout="centered",
)

# ── Session state ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "token" not in st.session_state:
    st.session_state.token = None
if "user_role" not in st.session_state:
    st.session_state.user_role = "admin"
if "user_id" not in st.session_state:
    st.session_state.user_id = "dev"

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏢 Enterprise RAG")
    st.markdown("---")

    st.subheader("User Settings")
    st.session_state.user_id = st.text_input("User ID", value=st.session_state.user_id)
    st.session_state.user_role = st.selectbox(
        "Role",
        ["admin", "hr_manager", "dept_head", "pm", "employee"],
        index=0,
    )

    if st.button("🔑 Get Token"):
        try:
            resp = requests.post(
                f"{API_URL}/token",
                json={"user_id": st.session_state.user_id, "role": st.session_state.user_role},
            )
            if resp.ok:
                st.session_state.token = resp.json()["access_token"]
                st.success("Token issued!")
            else:
                st.error(f"Error: {resp.text}")
        except requests.ConnectionError:
            st.error("Cannot connect to API. Is the server running?")

    st.markdown("---")
    st.subheader("System Status")
    try:
        health = requests.get(f"{API_URL}/health", timeout=3).json()
        st.success(f"API: {health['status']}")
        st.info(f"Index loaded: {health.get('index_loaded', 'N/A')}")
    except Exception:
        st.error("API offline")

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ── Chat interface ───────────────────────────────────────────────────
st.title("💬 Enterprise RAG Assistant")
st.caption("Ask questions about your databases, policies, and documents.")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            with st.expander("Details"):
                st.json(msg["meta"])

# User input
if prompt := st.chat_input("Ask a question..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            headers = {}
            if st.session_state.token:
                headers["Authorization"] = f"Bearer {st.session_state.token}"

            try:
                resp = requests.post(
                    f"{API_URL}/ask",
                    json={"question": prompt, "user_id": st.session_state.user_id},
                    headers=headers,
                    timeout=120,
                )

                if resp.ok:
                    data = resp.json()
                    answer = data.get("answer", "No response received.")
                    st.markdown(answer)

                    meta = {}
                    if data.get("intent"):
                        meta["intent"] = data["intent"]
                    if data.get("source"):
                        meta["source"] = data["source"]
                    if data.get("sql"):
                        meta["sql"] = data["sql"]
                    if data.get("total_rows") is not None:
                        meta["total_rows"] = data["total_rows"]

                    if meta:
                        with st.expander("Details"):
                            st.json(meta)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "meta": meta if meta else None,
                    })
                else:
                    err = f"API error: {resp.status_code} — {resp.text}"
                    st.error(err)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": err,
                    })

            except requests.ConnectionError:
                st.error("Cannot connect to the API server. Please ensure it is running.")
            except requests.Timeout:
                st.error("Request timed out. The LLM may be processing a complex query.")

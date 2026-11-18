"""Customer chat UI (FR-08). Run: streamlit run services/ui/chat_app.py"""

from __future__ import annotations

import os
import uuid

import httpx
import streamlit as st

API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000")

st.set_page_config(page_title="ShopX Support", page_icon="💬")
st.title("💬 ShopX Customer Support")

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about shipping, returns, your order..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    resp = httpx.post(
        f"{API_URL}/v1/chat",
        json={"session_id": st.session_state.session_id, "message": prompt},
        timeout=30,
    ).json()

    with st.chat_message("assistant"):
        st.markdown(resp["answer"])
        # TODO(FR-08): render citations nicely (expanders with doc_id + snippet).
        for c in resp.get("citations", []):
            st.caption(f"📄 {c['doc_id']}: {c['snippet'][:120]}…")
    st.session_state.messages.append({"role": "assistant", "content": resp["answer"]})

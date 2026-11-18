"""Store-manager dashboard (FR-07). Run: streamlit run services/dashboard/app.py"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Shelf Monitoring", page_icon="🛒", layout="wide")
st.title("🛒 Retail Shelf Monitoring")

try:
    health = httpx.get(f"{API_URL}/health", timeout=5).json()
    st.caption(f"API {health['version']} · model {health['model_version']}")
except httpx.HTTPError:
    st.error(f"API not reachable at {API_URL}")

tab_upload, tab_history, tab_alerts = st.tabs(["Analyze", "History", "Alerts"])

with tab_upload:
    # TODO(FR-01, FR-02): upload an image → POST /v1/analyze → show annotated image + metrics.
    st.file_uploader("Shelf photo", type=["jpg", "jpeg", "png"])
    st.text_input("Store ID", value="S001")

with tab_history:
    # TODO(FR-05, FR-07): GET /v1/analyses with store / date filters → table + fill-rate chart.
    st.info("History not implemented yet (FR-05, FR-07).")

with tab_alerts:
    # TODO(FR-07): list open alerts, button to mark as resolved.
    st.info("Alerts not implemented yet (FR-07).")

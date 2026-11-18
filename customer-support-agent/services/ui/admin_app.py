"""Admin UI for support staff: list tickets and update their status (FR-08).

Run: streamlit run services/ui/admin_app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="ShopX Support – Admin", page_icon="🎫")
st.title("🎫 Ticket queue")

# TODO(FR-08): fetch tickets from the Ticket Service (GET /v1/tickets), show them in st.dataframe,
# allow filtering by status/priority and updating status (open → in_progress → resolved).
st.info("Ticket list not implemented yet (FR-05, FR-08).")

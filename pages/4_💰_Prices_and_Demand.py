"""Prices & Demand page — electricity, heat, hydrogen prices and demand."""
from __future__ import annotations

import streamlit as st

from lib import data

data.ensure_state()
st.title("💰 Prices and Demand")

if not data.list_scenarios():
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

# TODO P4: price comparison bar chart per commodity
# TODO P4: hourly price line plot per region (if STyly resolution available)
# TODO P4: demand vs supply summary

st.markdown(
    "_This page is a stub. Implementation lands in **Phase 4**:_\n"
    "- Average price per commodity (electricity, heat, hydrogen) × scenario\n"
    "- Hourly price line plots when STyly resolution is in the archive\n"
    "- Demand breakdown by category × country"
)

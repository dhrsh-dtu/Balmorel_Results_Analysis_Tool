"""Transmission page — line capacities and inter-regional flows."""
from __future__ import annotations

import streamlit as st

from lib import data

data.ensure_state()
st.title("🔌 Transmission")

if not data.list_scenarios():
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

# TODO P6: flow matrix heatmap (from × to) per commodity
# TODO P6: net trade bar chart per country
# TODO P6: capacity ranking by line

st.markdown(
    "_This page is a stub. Implementation lands in **Phase 6**:_\n"
    "- Flow matrix heatmap (From × To) per commodity (Electricity, H2, Heat)\n"
    "- Net trade bar chart per country\n"
    "- Top transmission lines by capacity"
)

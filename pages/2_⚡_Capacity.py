"""Capacity page — installed generation capacity by tech/fuel/country."""
from __future__ import annotations

import streamlit as st

from lib import data

data.ensure_state()
st.title("⚡ Capacity")

if not data.list_scenarios():
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

# TODO P3: stacked bar Scenario × Technology, faceted by Country
# TODO P3: heatmap Country × Tech
# TODO P3: sortable table + CSV download

st.markdown(
    "_This page is a stub. Implementation lands in **Phase 3**:_\n"
    "- Stacked bars by Scenario × Technology, faceted by Country\n"
    "- Toggles: Technology vs Fuel grouping, Endo/Exo filter\n"
    "- Heatmap: Country × Tech (GW)\n"
    "- Sortable table + CSV download"
)

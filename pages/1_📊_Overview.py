"""Overview page — KPIs and high-level summary across selected scenarios."""
from __future__ import annotations

import streamlit as st

from lib import data

data.ensure_state()
st.title("📊 Overview")

if not data.list_scenarios():
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

# TODO P2: KPI metric row (total cost, total capacity, total production, max TL)
# TODO P2: Cost stacked bar by scenario × OBJ_YCR Category
# TODO P2: Capacity mix mini-stacks per commodity

st.markdown(
    "_This page is a stub. Implementation lands in **Phase 2**:_\n"
    "- KPI metric row: total cost, capacity, production, max planetary-boundary transgression\n"
    "- Cost stacked bar (`OBJ_YCR` × Category) per scenario\n"
    "- Capacity mix mini-stacks per commodity"
)

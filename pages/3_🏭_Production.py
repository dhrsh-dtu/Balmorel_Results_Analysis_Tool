"""Production page — annual production by tech/fuel/country."""
from __future__ import annotations

import streamlit as st

from lib import data

data.ensure_state()
st.title("🏭 Production")

if not data.list_scenarios():
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

# TODO P3: stacked bars Scenario × Country × Tech
# TODO P3: production share donut per scenario
# TODO P3 (optional): hourly dispatch profile per region/commodity

st.markdown(
    "_This page is a stub. Implementation lands in **Phase 3**:_\n"
    "- Annual production stacked bars (Scenario × Country × Tech)\n"
    "- Production share donut per scenario\n"
    "- (Optional) hourly dispatch profile per region/commodity"
)

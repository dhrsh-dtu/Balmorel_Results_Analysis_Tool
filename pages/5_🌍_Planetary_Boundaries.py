"""Planetary Boundaries page — TL_*/IS_* indicators.

Auto-hides itself with a message if no PB symbols are loaded.
"""
from __future__ import annotations

import streamlit as st

from lib import data, schemas

data.ensure_state()
st.title("🌍 Planetary Boundaries")

if not data.list_scenarios():
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

has_any_pb = any(schemas.has_pb_symbols(s.symbols) for s in data.selected_scenarios())
if not has_any_pb:
    st.warning(
        "🌍 None of the selected scenarios contain Planetary Boundary symbols (`TL_*`, `IS_*`). "
        "This page is only meaningful for Balmorel runs using the PB extension."
    )
    st.stop()

# TODO P5: radar plot of all TL_* indicators across scenarios with boundary ring at 1.0
# TODO P5: indicator drill-down — pick one impact → IS_*_FFF stacked bar by fuel/tech
# TODO P5: attribution split — IS_* (generation) vs IS_*_X (transmission) vs IS_*_X_H2 vs IS_*_EV

st.markdown(
    "_This page is a stub. Implementation lands in **Phase 5**:_\n"
    "- Radar/spider chart of all `TL_*` indicators across scenarios with boundary ring at 1.0\n"
    "- Indicator drill-down: stacked bar of `IS_*_FFF` contributions by fuel/tech\n"
    "- Attribution split: generation vs transmission vs H2 transmission vs EVs"
)

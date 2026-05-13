"""Raw Explorer — pick any symbol, see the DataFrame, filter, download as CSV.

Always available; useful escape hatch for users wanting custom analysis.
"""
from __future__ import annotations

import streamlit as st

from lib import data

data.ensure_state()
st.title("🔍 Raw Explorer")

if not data.list_scenarios():
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

scns = data.selected_scenarios()
all_symbols = sorted({sym for s in scns for sym in s.symbols})

if not all_symbols:
    st.warning("Selected scenarios have no symbols loaded.")
    st.stop()

symbol = st.selectbox("Symbol", options=all_symbols)
df = data.get_table(symbol, scenarios=scns)

if df.empty:
    st.warning(f"`{symbol}` is empty in the selected scenarios.")
    st.stop()

st.caption(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
st.dataframe(df, use_container_width=True, height=500)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇ Download CSV",
    data=csv,
    file_name=f"{symbol}.csv",
    mime="text/csv",
)

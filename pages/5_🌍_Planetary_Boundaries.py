"""Planetary Boundaries page — TL_*/IS_* indicators.

Auto-hides cleanly if no PB symbols are loaded.

Sections:
  1. Overall radar across all indicators × scenarios (with boundary ring at TL=1.0)
  2. Summary table (TL per indicator per scenario, color-coded)
  3. Indicator drill-down — transgression bar, source attribution, fuel/tech breakdown
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import data, plots, schemas

data.ensure_state()
st.title("🌍 Planetary Boundaries")

scns = data.selected_scenarios()
if not scns:
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

has_any_pb = any(schemas.has_pb_symbols(s.symbols) for s in scns)
if not has_any_pb:
    st.warning(
        "🌍 None of the selected scenarios contain Planetary Boundary symbols "
        "(`TL_*`, `IS_*`). This page is only meaningful for Balmorel runs that "
        "use the PB extension."
    )
    st.stop()

st.caption(
    f"Showing **{len(scns)}** scenario(s)  ·  Year: **{data.selected_year() or '—'}**  ·  "
    f"PB indicators: **{', '.join(data.pb_indicators_present(scns)) or '—'}**"
)

# ── 1. Overall radar ─────────────────────────────────────────────────────────
st.markdown("### Overall transgression")

# Build {scenario: {indicator: TL_value}} dict for the radar
radar_data: dict[str, dict[str, float]] = {}
for s in scns:
    for sym, df in s.tables.items():
        if sym.startswith("TL_") and not df.empty and "Value" in df.columns:
            ind = sym.removeprefix("TL_")
            try:
                radar_data.setdefault(s.name, {})[ind] = float(df["Value"].astype(float).sum())
            except (ValueError, TypeError):
                continue

if not radar_data:
    st.info("No `TL_*` data in selected scenarios.")
else:
    st.plotly_chart(plots.pb_radar(radar_data, boundary=1.0), use_container_width=True)
    st.caption(
        "**Boundary ring** at TL = 1.0. Polygons inside the ring = within boundary; "
        "outside the ring = transgressed."
    )

st.divider()

# ── 2. Summary table ────────────────────────────────────────────────────────
st.markdown("### Transgression summary")

tl_df = data.pb_transgression_table(scns)
if tl_df.empty:
    st.info("No transgression-level data.")
else:
    pivot = (
        tl_df.pivot(index="Indicator", columns="Scenario", values="TL")
        .fillna(0.0)
        .sort_index()
    )
    pivot["Boundary"] = 1.0

    def _color(v):
        try:
            x = float(v)
        except (ValueError, TypeError):
            return ""
        if x >= 1.0:
            return "background-color: #ffd9d9; color: #b30000; font-weight: bold"
        if x >= 0.75:
            return "background-color: #fff3cd; color: #856404"
        return "color: #2c7a3a"

    style = (
        pivot.style.format("{:.4f}")
        .map(_color, subset=[c for c in pivot.columns if c != "Boundary"])
    )
    st.dataframe(style, use_container_width=True)

    st.download_button(
        "⬇ Download summary CSV",
        data=pivot.to_csv().encode("utf-8"),
        file_name="pb_transgression_summary.csv",
        mime="text/csv",
    )

st.divider()

# ── 3. Indicator drill-down ─────────────────────────────────────────────────
st.markdown("### Indicator drill-down")

available_inds = data.pb_indicators_present(scns)
if not available_inds:
    st.info("No PB indicators available for drill-down.")
    st.stop()

c1, c2 = st.columns([0.6, 0.4])
with c1:
    indicator = st.selectbox(
        "Indicator",
        options=available_inds,
        format_func=lambda x: x.replace("_", " ").title(),
    )
with c2:
    group_by = st.radio(
        "Generation breakdown by",
        ["Fuel", "Technology"],
        horizontal=True,
        key="pb_group_by",
    )

# ── 3a. TL bar with boundary line ───────────────────────────────────────────
ind_tl = tl_df[tl_df["Indicator"] == indicator]
st.markdown(f"#### Transgression level — {indicator.replace('_', ' ').title()}")
st.plotly_chart(
    plots.pb_transgression_bar(
        ind_tl,
        boundary=1.0,
        title=None,
    ),
    use_container_width=True,
)

# ── 3b. Source attribution stack ────────────────────────────────────────────
st.markdown(f"#### Impact-score attribution — {indicator.replace('_', ' ').title()}")
attr_df = data.pb_attribution_table(indicator, scenarios=scns)
if attr_df.empty:
    st.info(f"No attribution data for `{indicator}` "
            "(expected one or more of `IS_<indicator>{_X,_X_H2,_EV}` symbols).")
else:
    st.plotly_chart(
        plots.pb_attribution_stack(
            attr_df,
            title=None,
            value_label=f"Impact score ({indicator})",
        ),
        use_container_width=True,
    )
    plots.show_table_with_download(
        attr_df.pivot(index="Source", columns="Scenario", values="Value").fillna(0.0),
        filename=f"pb_{indicator}_attribution",
        label="📋 Attribution table",
        fmt="{:.3e}",
    )

# ── 3c. Fuel / technology breakdown of the generation component ─────────────
st.markdown(f"#### Generation breakdown by {group_by.lower()} — {indicator.replace('_', ' ').title()}")
fb_df = data.pb_fuel_breakdown(indicator, group_by=group_by, scenarios=scns)
if fb_df.empty:
    st.info(f"No `IS_{indicator}_FFF` data for fuel/tech breakdown.")
else:
    min_show = st.number_input(
        "Min |impact| to display",
        min_value=0.0, value=0.0, step=1.0, format="%.2e",
        help="Hide contributions with |impact| below this threshold. "
             "Useful when many fuels contribute near-zero values.",
        key="pb_min_show",
    )
    st.plotly_chart(
        plots.pb_fuel_breakdown_bar(
            fb_df,
            group_by=group_by,
            title=None,
            value_label=f"IS_{indicator}",
            min_abs_value=min_show,
        ),
        use_container_width=True,
    )
    plots.show_table_with_download(
        fb_df.pivot(index=group_by, columns="Scenario", values="Value").fillna(0.0),
        filename=f"pb_{indicator}_by_{group_by.lower()}",
        label=f"📋 {group_by} breakdown table",
        fmt="{:.3e}",
    )

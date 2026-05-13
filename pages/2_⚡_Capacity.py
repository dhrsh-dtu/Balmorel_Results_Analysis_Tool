"""Capacity page — installed generation capacity by tech/fuel/country, plus storage."""
from __future__ import annotations

import streamlit as st

from lib import data, plots

data.ensure_state()
st.title("⚡ Capacity")

scns = data.selected_scenarios()
if not scns:
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

st.caption(
    f"Showing **{len(scns)}** scenario(s)  ·  Year: **{data.selected_year() or '—'}**  ·  "
    f"Countries: {', '.join(data.selected_countries() or ['all'])}"
)

gen_tab, sto_tab = st.tabs(["Generation capacity", "Storage capacity"])

# ── Generation capacity ─────────────────────────────────────────────────────
with gen_tab:
    cap_df = data.get_filtered("G_CAP_YCRAF")
    if cap_df.empty:
        st.info("No `G_CAP_YCRAF` data in selected scenarios.")
    else:
        # ── Controls ────────────────────────────────────────────────────────
        c1, c2, c3 = st.columns(3)
        with c1:
            color_by = st.radio(
                "Color by",
                ["Technology", "Fuel"],
                horizontal=True,
                key="cap_color_by",
            )
        with c2:
            available_cats = (
                sorted(cap_df["Category"].dropna().unique())
                if "Category" in cap_df.columns else []
            )
            if available_cats:
                cat_filter = st.radio(
                    "Category",
                    ["Both"] + available_cats,
                    horizontal=True,
                    key="cap_category",
                )
                if cat_filter != "Both":
                    cap_df = cap_df[cap_df["Category"] == cat_filter]
        with c3:
            min_cap = st.number_input(
                "Min display (GW)",
                min_value=0.0, value=0.01, step=0.01, format="%.2f",
                help="Hide capacity entries below this threshold.",
                key="cap_min",
            )

        # ── Plot 1: Stacked by Scenario × Commodity ─────────────────────────
        st.markdown("#### Total installed capacity")
        st.plotly_chart(
            plots.capacity_by_commodity(cap_df, color_by=color_by, min_capacity=min_cap),
            use_container_width=True,
        )

        # ── Plot 2: By country, faceted by scenario × commodity ────────────
        st.markdown("#### By country")
        st.plotly_chart(
            plots.by_country_stacked_bar(
                cap_df,
                color_by=color_by,
                value_label="GW",
                facet_by_commodity=True,
                min_value=min_cap,
                title=f"Capacity by country, scenario, and {color_by.lower()} (GW)",
            ),
            use_container_width=True,
        )

        # ── Plot 3: Heatmap Country × Technology ────────────────────────────
        st.markdown("#### Heatmap: country × " + color_by.lower())
        st.plotly_chart(
            plots.country_tech_heatmap(
                cap_df,
                rows="Country",
                cols=color_by,
                value_label="GW",
                title=None,
            ),
            use_container_width=True,
        )

        # ── Detail table ────────────────────────────────────────────────────
        pivot = (
            cap_df.groupby(["Scenario", "Country", color_by], observed=True)["Value"]
            .sum()
            .unstack(color_by, fill_value=0)
            .reset_index()
        )
        plots.show_table_with_download(
            pivot.set_index(["Scenario", "Country"]),
            filename="capacity_by_country",
            label="📋 Detail table",
        )

# ── Storage capacity ────────────────────────────────────────────────────────
with sto_tab:
    sto_df = data.get_filtered("G_STO_YCRAF")
    if sto_df.empty:
        st.info(
            "No `G_STO_YCRAF` storage data in selected scenarios.\n\n"
            "_Some Balmorel runs don't model storage; this section will be empty in that case._"
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            color_by = st.radio(
                "Color by",
                ["Technology", "Fuel"],
                horizontal=True,
                key="sto_color_by",
            )
        with c2:
            min_sto = st.number_input(
                "Min display",
                min_value=0.0, value=0.001, step=0.001, format="%.3f",
                key="sto_min",
            )

        # Storage units vary (GWh for energy storage, GW for power) — read from Unit column
        unit = (
            sto_df["Unit"].dropna().mode().iat[0]
            if "Unit" in sto_df.columns and not sto_df["Unit"].dropna().empty
            else "Value"
        )

        st.markdown("#### Total storage capacity")
        st.plotly_chart(
            plots.capacity_by_commodity(sto_df, color_by=color_by, min_capacity=min_sto),
            use_container_width=True,
        )

        st.markdown("#### Storage capacity by country")
        st.plotly_chart(
            plots.by_country_stacked_bar(
                sto_df,
                color_by=color_by,
                value_label=unit,
                facet_by_commodity=True,
                min_value=min_sto,
            ),
            use_container_width=True,
        )

        pivot = (
            sto_df.groupby(["Scenario", "Country", color_by], observed=True)["Value"]
            .sum()
            .unstack(color_by, fill_value=0)
            .reset_index()
        )
        plots.show_table_with_download(
            pivot.set_index(["Scenario", "Country"]),
            filename="storage_capacity",
            label="📋 Detail table",
        )

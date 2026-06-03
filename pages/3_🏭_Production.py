"""Production page — annual production by tech/fuel/country."""
from __future__ import annotations

import streamlit as st

from lib import data, plots

data.ensure_state()
st.title("🏭 Production")

data.render_page_filters("production")
scns = data.selected_scenarios()
if not scns:
    st.info("Upload at least one scenario archive in the sidebar to see content.")
    st.stop()

st.caption(
    f"Showing **{len(scns)}** scenario(s)  ·  Year: **{data.selected_year() or '—'}**  ·  "
    f"Countries: {', '.join(data.selected_countries() or ['all'])}"
)

pro_df = data.get_filtered("PRO_YCRAGF")
if pro_df.empty:
    st.info("No `PRO_YCRAGF` data in selected scenarios.")
    st.stop()

annual_tab, country_tab, mix_tab = st.tabs(["Annual totals", "By country", "Mix per scenario"])

# ── Controls (shared across tabs) ────────────────────────────────────────────
controls = st.container()
with controls:
    c1, c2, c3 = st.columns(3)
    with c1:
        color_by = st.radio(
            "Color by",
            ["Technology", "Fuel"],
            horizontal=True,
            key="prod_color_by",
        )
    with c2:
        commodities = (
            sorted(pro_df["Commodity"].dropna().unique())
            if "Commodity" in pro_df.columns else []
        )
        commodity_filter = st.radio(
            "Commodity",
            ["All"] + commodities,
            horizontal=True,
            key="prod_commodity",
        )
    with c3:
        min_prod = st.number_input(
            "Min display (TWh)",
            min_value=0.0, value=0.001, step=0.01, format="%.3f",
            key="prod_min",
        )

filtered = pro_df if commodity_filter == "All" else pro_df[pro_df["Commodity"] == commodity_filter]

# ── Annual totals ────────────────────────────────────────────────────────────
with annual_tab:
    # FIX: On the production page, the y axis label (GW instead of TWh) and title (installed capacity instead of prod.) was wrong
    st.markdown("#### Annual production by commodity")
    if commodity_filter == "All":
        # Show faceted by commodity
        st.plotly_chart(
            plots.capacity_by_commodity(
                # capacity_by_commodity works generically for any (Scenario, Commodity, color_by, Value)
                filtered.rename(columns={}),  # no-op rename for clarity
                color_by=color_by,
                min_capacity=min_prod,
            ),
            use_container_width=True,
        )
    else:
        # Single commodity — simpler stack
        agg = (
            filtered.groupby(["Scenario", color_by], observed=True)["Value"]
            .sum()
            .reset_index()
        )
        agg = agg[agg["Value"].abs() >= min_prod]
        if agg.empty:
            st.info("All values below the display threshold.")
        else:
            import plotly.express as px
            from lib.theme import TECH_FUEL_COLORS
            fig = px.bar(
                agg, x="Scenario", y="Value", color=color_by,
                color_discrete_map=TECH_FUEL_COLORS,
                title=f"Annual {commodity_filter.title()} production (TWh)",
                labels={"Value": "TWh"},
            )
            fig.update_layout(barmode="stack", height=460)
            fig.update_traces(
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:,.2f} TWh<extra></extra>"
            )
            st.plotly_chart(fig, use_container_width=True)

    # Table
    pivot = (
        filtered.groupby(["Scenario", "Commodity", color_by], observed=True)["Value"]
        .sum()
        .unstack(color_by, fill_value=0)
        .reset_index()
    )
    plots.show_table_with_download(
        pivot.set_index(["Scenario", "Commodity"]),
        filename="production_annual",
        label="📋 Detail table",
    )

# ── By country ───────────────────────────────────────────────────────────────
with country_tab:
    # FIX: Maybe simply make this plot much longer, so you can actually see the plots
    st.markdown("#### Production by country")
    st.plotly_chart(
        plots.by_country_stacked_bar(
            filtered,
            color_by=color_by,
            value_label="TWh",
            facet_by_commodity=(commodity_filter == "All"),
            min_value=min_prod,
            title=None,
        ),
        use_container_width=True,
    )
    pivot = (
        filtered.groupby(["Scenario", "Country", "Commodity", color_by], observed=True)["Value"]
        .sum()
        .unstack(color_by, fill_value=0)
        .reset_index()
    )
    plots.show_table_with_download(
        pivot.set_index(["Scenario", "Country", "Commodity"]),
        filename="production_by_country",
        label="📋 Detail table",
    )

# ── Mix per scenario (donuts) ───────────────────────────────────────────────
with mix_tab:
    st.markdown("#### Production mix per scenario")
    if commodity_filter == "All":
        # Show one donut row per commodity
        for c in commodities:
            st.markdown(f"**{c.title()}**")
            st.plotly_chart(
                plots.production_share_donuts(
                    pro_df,
                    commodity=c,
                    color_by=color_by,
                ),
                use_container_width=True,
            )
    else:
        st.plotly_chart(
            plots.production_share_donuts(
                pro_df,
                commodity=commodity_filter,
                color_by=color_by,
            ),
            use_container_width=True,
        )
